"""
app.py — La app web del CRM (Fase 1: ver venues).

Abre dos pantallas en el navegador:
  /            -> la LISTA de venues, con filtros (ciudad, artista, estado, categoria).
  /venue/<id>  -> la FICHA de un venue (todos sus datos).

Para arrancar:   python3 app.py
Luego abre:      http://localhost:5000
"""

import re
from datetime import date
from urllib.parse import quote_plus

from flask import Flask, render_template, request, abort, redirect, url_for

import database
import places_search
import artistas
import ai_email
import plantillas
import email_sender
import enrich
import cadencia

app = Flask(__name__)


@app.context_processor
def utilidades():
    """Funciones disponibles en las plantillas."""

    def enlace_google(place_id, nombre=""):
        """Arma el enlace directo a la ficha del lugar en Google Maps / My Business.

        Usa el formato oficial de Google (Maps URLs API) a partir del place_id
        que ya guardamos, asi que no hace falta pedir nada extra a la API.
        """
        if not place_id:
            return None
        return (
            "https://www.google.com/maps/search/?api=1"
            "&query=" + quote_plus(nombre or "venue")
            + "&query_place_id=" + place_id
        )

    def _solo_digitos_intl(telefono):
        """Convierte un telefono a digitos con codigo de pais. USA por defecto (+1
        si son 10 digitos). Cuando entremos a Mexico se ajusta el +52."""
        if not telefono:
            return None
        digitos = re.sub(r"\D", "", telefono)
        if len(digitos) == 10:  # numero local de USA -> anteponer 1
            digitos = "1" + digitos
        return digitos or None

    def enlace_whatsapp(telefono):
        """Enlace wa.me para abrir el chat (tu escribes; la app no envia nada)."""
        d = _solo_digitos_intl(telefono)
        return "https://wa.me/" + d if d else None

    def enlace_llamada(telefono):
        """Enlace tel: para marcar desde el telefono/Mac."""
        d = _solo_digitos_intl(telefono)
        return "tel:+" + d if d else None

    return dict(
        enlace_google=enlace_google,
        enlace_whatsapp=enlace_whatsapp,
        enlace_llamada=enlace_llamada,
        hoy=date.today().isoformat(),
    )


@app.route("/")
def inicio():
    """Panel de inicio: números de un vistazo."""
    total_venues = len(database.listar_venues())
    por_estado = database.contar_por("estado_pipeline", "venues")
    por_artista = database.contar_por("artista", "venues")
    msg_estados = database.contar_por("estado", "mensajes")
    # Orden lógico del pipeline para mostrar los chips.
    orden_pipeline = ["nuevo", "calificado", "contactado", "respondió",
                      "negociando", "cerrado", "descartado"]
    pipeline = [(e, por_estado.get(e, 0)) for e in orden_pipeline if por_estado.get(e, 0)]
    return render_template(
        "inicio.html",
        total_venues=total_venues,
        pipeline=pipeline,
        por_artista=por_artista,
        msg_estados=msg_estados,
        enviados_semana=database.contar_enviados_recientes(7),
        recordatorios=database.listar_recordatorios()[:6],
        seguimiento_conteos=cadencia.conteos(),
    )


@app.route("/venues")
def lista():
    # Lee los filtros que vengan en la URL (vacios = sin filtro).
    ciudad = request.args.get("ciudad") or None
    artista = request.args.get("artista") or None
    estado_pipeline = request.args.get("estado_pipeline") or None
    categoria = request.args.get("categoria") or None
    buscar = request.args.get("q") or None
    email_filtro = request.args.get("email") or ""  # 'si' | 'no' | ''
    con_email = True if email_filtro == "si" else (False if email_filtro == "no" else None)

    venues = database.listar_venues(
        ciudad=ciudad,
        artista=artista,
        estado_pipeline=estado_pipeline,
        categoria=categoria,
        buscar=buscar,
        con_email=con_email,
    )

    # Opciones para los menus de filtro (valores que existen en la base).
    filtros = {
        "ciudades": database.valores_distintos("ciudad"),
        "artistas": database.valores_distintos("artista"),
        "estados_pipeline": database.valores_distintos("estado_pipeline"),
        "categorias": database.valores_distintos("categoria"),
    }
    seleccion = {
        "ciudad": ciudad or "",
        "artista": artista or "",
        "estado_pipeline": estado_pipeline or "",
        "categoria": categoria or "",
        "q": buscar or "",
        "email": email_filtro,
    }

    return render_template("lista.html", venues=venues, filtros=filtros, seleccion=seleccion)


@app.route("/venue/<int:venue_id>")
def ficha(venue_id):
    venue = database.obtener_venue(venue_id)
    if venue is None:
        abort(404)
    guardado = request.args.get("guardado")  # mensaje "cambios guardados"
    actividades = database.listar_actividades(venue_id)
    mensajes = database.listar_mensajes(venue_id)
    perfil = artistas.obtener(venue["artista"]) if venue["artista"] else None
    ganchos = perfil.get("ganchos", []) if perfil else []
    # ¿El perfil del artista todavía tiene placeholders [..] sin llenar?
    perfil_incompleto = False
    if perfil:
        texto_perfil = perfil.get("bio", "") + " ".join(perfil.get("links", []))
        perfil_incompleto = "[" in texto_perfil
    # Plantillas fijas: asuntos por idioma (para los menús) y si falta el brochure.
    artista = venue["artista"]
    hay_plantillas = bool(artista and plantillas.tiene(artista))
    asuntos_por_idioma = plantillas.asuntos_por_idioma(artista) if hay_plantillas else {}
    brochure_falta = bool(hay_plantillas and not plantillas.brochure_de(artista))
    return render_template(
        "ficha.html",
        v=venue,
        guardado=guardado,
        actividades=actividades,
        mensajes=mensajes,
        ganchos=ganchos,
        perfil_incompleto=perfil_incompleto,
        hay_plantillas=hay_plantillas,
        asuntos_por_idioma=asuntos_por_idioma,
        idioma_default=(perfil.get("idioma_correo", "en") if perfil else "en"),
        brochure_falta=brochure_falta,
        enviados_semana=database.contar_enviados_recientes(7),
        correo_ok=request.args.get("correo_ok"),
        correo_error=request.args.get("correo_error"),
        enriq_ok=request.args.get("enriq_ok"),
        enriq_error=request.args.get("enriq_error"),
    )


# Campos que el formulario de la ficha puede editar.
CAMPOS_FORM = [
    "categoria", "artista", "ciudad", "estado", "direccion", "telefono", "web",
    "pagina_booking", "email", "redes", "encargado", "capacidad", "genero",
    "mejor_canal", "proxima_accion", "recordatorio_fecha", "notas",
]


@app.route("/venue/<int:venue_id>/guardar", methods=["POST"])
def guardar(venue_id):
    if database.obtener_venue(venue_id) is None:
        abort(404)
    # Solo tocar los campos que realmente vienen en el formulario (evita borrar datos
    # si llega un envio parcial). Un campo vacio si limpia ese campo (a None).
    cambios = {c: (request.form.get(c) or None) for c in CAMPOS_FORM if c in request.form}
    database.actualizar_venue(venue_id, cambios)
    return redirect(url_for("ficha", venue_id=venue_id, guardado="1"))


@app.route("/venue/<int:venue_id>/decidir", methods=["POST"])
def decidir(venue_id):
    if database.obtener_venue(venue_id) is None:
        abort(404)
    accion = request.form.get("accion")
    # Aprobacion #1: calificar (sirve), descartar (no sirve), o reabrir (volver a 'nuevo').
    mapa = {"calificar": "calificado", "descartar": "descartado", "reabrir": "nuevo"}
    nuevo_estado = mapa.get(accion)
    if nuevo_estado:
        database.actualizar_venue(venue_id, {"estado_pipeline": nuevo_estado})
    return redirect(url_for("ficha", venue_id=venue_id))


@app.route("/venue/<int:venue_id>/enriquecer", methods=["POST"])
def enriquecer_venue(venue_id):
    """Fase 2: entra a la web del venue y busca correo / página de booking / redes.
    Rellena solo esos campos del venue (no borra lo que ya tengas escrito a mano)."""
    venue = database.obtener_venue(venue_id)
    if venue is None:
        abort(404)
    destino = url_for("ficha", venue_id=venue_id)
    if not venue["web"]:
        return redirect(destino + "?enriq_error=Este venue no tiene sitio web; agrégalo abajo primero.")
    try:
        datos = enrich.enriquecer_uno(venue)
        # No pisar con vacío lo que ya exista: solo guardar lo que se encontró.
        encontrado = {k: v for k, v in datos.items() if k == "enriquecido_el" or v}
        database.actualizar_venue(venue_id, encontrado)
        partes = []
        if datos.get("email"):
            partes.append("correo (" + datos["email"] + ")")
        if datos.get("pagina_booking"):
            partes.append("página de booking")
        if datos.get("redes"):
            partes.append("redes")
        if partes:
            msg = "Encontrado: " + ", ".join(partes) + ". Revísalo abajo."
        else:
            msg = "No se encontró correo en su web (puede estar tras un formulario). Revisa la página de booking a mano."
        return redirect(destino + f"?enriq_ok={msg}")
    except Exception as e:
        return redirect(destino + f"?enriq_error=No se pudo leer la web: {e}")


# Cuántos venues enriquecer como máximo por tanda (para no dejar la página colgada).
MAX_ENRIQUECER_LOTE = 15


@app.route("/artista/<nombre>/enriquecer", methods=["POST"])
def enriquecer_artista(nombre):
    """Fase 2 en lote: enriquece los venues de este artista que tengan web y aún no
    se hayan enriquecido (hasta MAX_ENRIQUECER_LOTE por tanda)."""
    perfil = artistas.obtener(nombre)
    if perfil is None:
        abort(404)
    destino = url_for("artista", nombre=nombre)
    venues = database.listar_venues(artista=nombre)
    pendientes = [v for v in venues if v["web"] and not v["enriquecido_el"]]
    if not pendientes:
        return redirect(destino + "?ok=No hay venues con web pendientes de enriquecer.")

    tanda = pendientes[:MAX_ENRIQUECER_LOTE]
    con_email = 0
    for v in tanda:
        try:
            datos = enrich.enriquecer_uno(v)
            encontrado = {k: val for k, val in datos.items() if k == "enriquecido_el" or val}
            database.actualizar_venue(v["id"], encontrado)
            if datos.get("email"):
                con_email += 1
        except Exception:
            # Si una web falla, seguimos con las demás (no abortamos toda la tanda).
            database.actualizar_venue(v["id"], {"enriquecido_el": date.today().isoformat()})
    restantes = len(pendientes) - len(tanda)
    msg = f"Enriquecidos {len(tanda)} venues: {con_email} quedaron con correo."
    if restantes:
        msg += f" Quedan {restantes} — vuelve a darle al botón para seguir."
    return redirect(destino + f"?ok={msg}")


@app.route("/venue/<int:venue_id>/actividad", methods=["POST"])
def registrar_actividad(venue_id):
    if database.obtener_venue(venue_id) is None:
        abort(404)
    database.agregar_actividad(
        venue_id=venue_id,
        canal=request.form.get("canal"),
        fecha=request.form.get("fecha") or None,
        resumen=request.form.get("resumen") or None,
        resultado=request.form.get("resultado") or None,
        siguiente_paso=request.form.get("siguiente_paso") or None,
    )
    return redirect(url_for("ficha", venue_id=venue_id) + "#actividades")


@app.route("/actividad/<int:actividad_id>/borrar", methods=["POST"])
def borrar_actividad(actividad_id):
    venue_id = database.eliminar_actividad(actividad_id)
    if venue_id is None:
        return redirect(url_for("lista"))
    return redirect(url_for("ficha", venue_id=venue_id) + "#actividades")


@app.route("/agenda")
def agenda():
    recordatorios = database.listar_recordatorios()
    return render_template("agenda.html", recordatorios=recordatorios)


@app.route("/seguimientos")
def seguimientos():
    """Cadencia (Fase 6A): a quién le toca follow-up hoy y quién está esperando."""
    toca, esperando = cadencia.seguimientos()
    return render_template(
        "seguimientos.html",
        toca=toca, esperando=esperando,
        gap=cadencia.GAP_POR_NUMERO,
    )


@app.route("/cola")
def cola():
    """Cola de llamada (Fase 6A): venues para gestión manual (llamada/WhatsApp/visita)."""
    items = cadencia.cola_llamada()
    return render_template("cola.html", items=items)


@app.route("/venue/<int:venue_id>/seguimiento", methods=["POST"])
def generar_seguimiento(venue_id):
    """Genera el borrador de un follow-up (por plantilla o IA) y lo deja en la ficha
    para revisar/aprobar/enviar. Nada se envía solo."""
    venue = database.obtener_venue(venue_id)
    if venue is None:
        abort(404)
    destino = url_for("ficha", venue_id=venue_id)

    artista = venue["artista"]
    if not artista or not plantillas.tiene(artista):
        return redirect(destino + "?correo_error=Asigna un artista con plantillas (Dani o Davikane).#correos")

    idioma = request.form.get("idioma") or ""
    try:
        numero = int(request.form.get("numero", 1))
    except (TypeError, ValueError):
        numero = 1
    modo = request.form.get("modo") or "plantilla"

    try:
        if modo == "ia":
            # Reusa la IA con una instrucción de seguimiento breve.
            instruccion = (
                "Este es un CORREO DE SEGUIMIENTO (follow-up) a un primer correo que no fue "
                "respondido. Hazlo MUY breve (50-90 palabras), cordial y sin presión: recuerda "
                "amablemente el correo anterior y reitera la invitación a una fecha. No repitas "
                "toda la bio."
            )
            b = ai_email.generar_borrador(venue, indice_gancho=0, instruccion=instruccion)
            perfil = artistas.obtener(artista) or {}
            database.agregar_mensaje(
                venue_id=venue_id, asunto=b["asunto"], cuerpo=b["cuerpo"],
                gancho=b["gancho"], modelo=b["modelo"],
                origen="seguimiento", idioma=perfil.get("idioma_correo"),
                version=f"F{numero}",
            )
        else:
            b = plantillas.generar_seguimiento(artista, venue, idioma=idioma, numero=numero)
            database.agregar_mensaje(
                venue_id=venue_id, asunto=b["asunto"], cuerpo=b["cuerpo"],
                modelo="plantilla v5 (seguimiento)", origen="seguimiento",
                idioma=b["idioma"], version=f"F{b['numero']}",
            )
        return redirect(destino + "?correo_ok=1#correos")
    except (ai_email.FaltaLlaveError, ai_email.GeneracionError) as e:
        return redirect(destino + f"?correo_error={e}#correos")
    except Exception as e:
        return redirect(destino + f"?correo_error=No se pudo generar el seguimiento: {e}#correos")


# Tipos de lugar -> (categoría A/B, plantilla de búsqueda para Google Places)
TIPOS_LUGAR = {
    "venues": ("A", "salas de conciertos y venues de música en vivo en {donde}"),
    "bares": ("A", "bares con música en vivo en {donde}"),
    "clubes": ("A", "clubes nocturnos y discotecas en {donde}"),
    "promotores": ("B", "promotores de eventos y empresas de eventos en {donde}"),
}


@app.route("/artista/<nombre>")
def artista(nombre):
    perfil = artistas.obtener(nombre)
    if perfil is None:
        abort(404)
    venues = database.listar_venues(artista=nombre)
    con_email = sum(1 for v in venues if v["email"])
    return render_template(
        "artista.html",
        nombre=nombre, perfil=perfil, venues=venues,
        total=len(venues), con_email=con_email,
        tipos=TIPOS_LUGAR,
        ok=request.args.get("ok"), error=request.args.get("error"),
    )


@app.route("/artista/<nombre>/buscar", methods=["POST"])
def buscar_lugares(nombre):
    perfil = artistas.obtener(nombre)
    if perfil is None:
        abort(404)
    ciudad = (request.form.get("ciudad") or "").strip()
    estado = (request.form.get("estado") or "").strip() or perfil.get("estado_default", "")
    tipo = request.form.get("tipo") or "venues"
    destino = url_for("artista", nombre=nombre)

    if not ciudad:
        return redirect(destino + "?error=Indica la ciudad para buscar.")

    categoria, plantilla = TIPOS_LUGAR.get(tipo, TIPOS_LUGAR["venues"])
    donde = ciudad + (f", {estado}" if estado else "")
    query = plantilla.format(donde=donde)
    try:
        r = places_search.buscar_y_guardar(
            query=query, artista=nombre, categoria=categoria,
            ciudad=ciudad, estado=estado, pais="USA", max_resultados=20,
        )
        msg = f"Búsqueda en {donde}: {r['nuevos']} nuevos, {r['repetidos']} ya estaban (de {r['total']})."
        return redirect(destino + f"?ok={msg}")
    except places_search.BusquedaError as e:
        return redirect(destino + f"?error={e}")
    except Exception as e:
        return redirect(destino + f"?error=No se pudo buscar: {e}")


@app.route("/venue/<int:venue_id>/generar-plantilla", methods=["POST"])
def generar_plantilla(venue_id):
    """Genera un borrador a partir de las plantillas FIJAS (no usa IA).

    Toma del formulario: idioma + versión del cuerpo (A/B) + asunto. El artista
    sale del venue. Rellena los huecos con el nombre del venue / encargado y el
    brochure del artista, y deja registrada la combinación usada.
    """
    venue = database.obtener_venue(venue_id)
    if venue is None:
        abort(404)
    destino = url_for("ficha", venue_id=venue_id)

    artista = venue["artista"]
    if not artista or not plantillas.tiene(artista):
        return redirect(destino + "?correo_error=Asigna un artista con plantillas (Dani o Davikane).#correos")

    idioma = request.form.get("idioma") or ""
    version = request.form.get("version") or "A"
    try:
        asunto_indice = int(request.form.get("asunto", 0))
    except (TypeError, ValueError):
        asunto_indice = 0

    try:
        b = plantillas.generar(artista, venue, idioma=idioma, version=version,
                               asunto_indice=asunto_indice)
        database.agregar_mensaje(
            venue_id=venue_id, asunto=b["asunto"], cuerpo=b["cuerpo"],
            modelo="plantilla v5", origen="plantilla",
            idioma=b["idioma"], version=b["version"], asunto_variante=b["asunto_variante"],
        )
        return redirect(destino + "?correo_ok=1#correos")
    except Exception as e:
        return redirect(destino + f"?correo_error=No se pudo generar la plantilla: {e}#correos")


@app.route("/venue/<int:venue_id>/generar-correo", methods=["POST"])
def generar_correo(venue_id):
    venue = database.obtener_venue(venue_id)
    if venue is None:
        abort(404)
    try:
        indice = int(request.form.get("gancho", 0))
    except (TypeError, ValueError):
        indice = 0
    instruccion = request.form.get("instruccion") or None
    try:
        borrador = ai_email.generar_borrador(venue, indice_gancho=indice, instruccion=instruccion)
        database.agregar_mensaje(
            venue_id=venue_id,
            asunto=borrador["asunto"],
            cuerpo=borrador["cuerpo"],
            gancho=borrador["gancho"],
            modelo=borrador["modelo"],
        )
        destino = url_for("ficha", venue_id=venue_id, correo_ok="1")
    except (ai_email.FaltaLlaveError, ai_email.GeneracionError) as e:
        destino = url_for("ficha", venue_id=venue_id, correo_error=str(e))
    except Exception as e:  # imprevisto — mostrarlo en lenguaje simple
        destino = url_for("ficha", venue_id=venue_id, correo_error=f"No se pudo generar: {e}")
    return redirect(destino + "#correos")


@app.route("/venue/<int:venue_id>/generar-variantes", methods=["POST"])
def generar_variantes(venue_id):
    venue = database.obtener_venue(venue_id)
    if venue is None:
        abort(404)
    instruccion = request.form.get("instruccion") or None
    perfil = artistas.obtener(venue["artista"]) if venue["artista"] else None
    ganchos = perfil.get("ganchos", []) if perfil else []
    if not ganchos:
        destino = url_for("ficha", venue_id=venue_id,
                          correo_error="No hay ganchos para este artista (revisa artistas.py).")
        return redirect(destino + "#correos")

    creados = 0
    error = None
    for i in range(len(ganchos)):
        try:
            b = ai_email.generar_borrador(venue, indice_gancho=i, instruccion=instruccion)
            database.agregar_mensaje(
                venue_id=venue_id, asunto=b["asunto"], cuerpo=b["cuerpo"],
                gancho=b["gancho"], modelo=b["modelo"],
            )
            creados += 1
        except (ai_email.FaltaLlaveError, ai_email.GeneracionError) as e:
            error = str(e)
            break  # si falla la llave/cuenta, no tiene sentido seguir

    if creados:
        destino = url_for("ficha", venue_id=venue_id, correo_ok=f"{creados}")
    else:
        destino = url_for("ficha", venue_id=venue_id,
                          correo_error=error or "No se pudo generar ninguna variante.")
    return redirect(destino + "#correos")


@app.route("/mensaje/<int:mensaje_id>/guardar", methods=["POST"])
def guardar_mensaje(mensaje_id):
    m = database.obtener_mensaje(mensaje_id)
    if m is None:
        abort(404)
    database.actualizar_mensaje(mensaje_id, {
        "asunto": request.form.get("asunto") or None,
        "cuerpo": request.form.get("cuerpo") or None,
    })
    return redirect(url_for("ficha", venue_id=m["venue_id"]) + "#correos")


@app.route("/mensaje/<int:mensaje_id>/decidir", methods=["POST"])
def decidir_mensaje(mensaje_id):
    m = database.obtener_mensaje(mensaje_id)
    if m is None:
        abort(404)
    accion = request.form.get("accion")
    mapa = {"aprobar": "aprobado", "reabrir": "borrador"}
    nuevo = mapa.get(accion)
    if nuevo:
        database.actualizar_mensaje(mensaje_id, {"estado": nuevo})
    return redirect(url_for("ficha", venue_id=m["venue_id"]) + "#correos")


@app.route("/mensaje/<int:mensaje_id>/borrar", methods=["POST"])
def borrar_mensaje(mensaje_id):
    venue_id = database.eliminar_mensaje(mensaje_id)
    if venue_id is None:
        return redirect(url_for("lista"))
    return redirect(url_for("ficha", venue_id=venue_id) + "#correos")


@app.route("/mensaje/<int:mensaje_id>/enviar", methods=["POST"])
def enviar_mensaje(mensaje_id):
    m = database.obtener_mensaje(mensaje_id)
    if m is None:
        abort(404)
    venue = database.obtener_venue(m["venue_id"])
    destino_url = url_for("ficha", venue_id=m["venue_id"])

    # Guardas de seguridad antes de enviar (esto sí sale al mundo).
    if m["estado"] != "aprobado":
        return redirect(destino_url + "?correo_error=Solo se envían borradores aprobados.#correos")
    if venue and venue["estado_pipeline"] == "descartado":
        return redirect(destino_url + "?correo_error=Este venue está descartado; no se envía.#correos")
    destinatario = (venue["email"].split(",")[0].strip() if venue and venue["email"] else "")
    if not destinatario:
        return redirect(destino_url + "?correo_error=El venue no tiene email; usa llamada o WhatsApp.#correos")

    try:
        sg_id = email_sender.enviar_correo(destinatario, m["asunto"], m["cuerpo"])
        database.marcar_enviado(mensaje_id, sg_id, destinatario)
        # Mueve el venue en el pipeline y deja registro en la línea de tiempo.
        if venue and venue["estado_pipeline"] in ("nuevo", "calificado"):
            database.actualizar_venue(venue["id"], {"estado_pipeline": "contactado"})
        database.agregar_actividad(
            venue_id=m["venue_id"], canal="correo",
            fecha=date.today().isoformat(),  # el día en que se hizo la gestión
            resumen=f"Correo enviado a {destinatario}: {m['asunto']}",
            resultado="enviado", siguiente_paso="Esperar respuesta / follow-up",
        )
        return redirect(destino_url + "?correo_ok=enviado#correos")
    except (email_sender.FaltaSendgridError, email_sender.EnvioError) as e:
        return redirect(destino_url + f"?correo_error={e}#correos")
    except Exception as e:
        return redirect(destino_url + f"?correo_error=No se pudo enviar: {e}#correos")


@app.route("/mensaje/<int:mensaje_id>/marcar", methods=["POST"])
def marcar_mensaje(mensaje_id):
    m = database.obtener_mensaje(mensaje_id)
    if m is None:
        abort(404)
    accion = request.form.get("accion")
    if accion == "abierto":
        database.marcar_tracking(mensaje_id, abierto=True)
    elif accion == "respondido":
        database.marcar_tracking(mensaje_id, respondido=True)
        # Si respondió, mueve el venue a 'respondió' en el pipeline.
        database.actualizar_venue(m["venue_id"], {"estado_pipeline": "respondió"})
    return redirect(url_for("ficha", venue_id=m["venue_id"]) + "#correos")


if __name__ == "__main__":
    # Asegura que la base exista antes de abrir la app (no borra nada).
    database.crear_base()
    # Puerto 5001: en Mac el 5000 lo ocupa AirPlay / Centro de Control.
    print("CRM Bragi corriendo en http://localhost:5001  (Ctrl+C para parar)")
    app.run(debug=True, port=5001)
