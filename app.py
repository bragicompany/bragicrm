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
import artistas
import ai_email
import email_sender

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
    )


@app.route("/venues")
def lista():
    # Lee los filtros que vengan en la URL (vacios = sin filtro).
    ciudad = request.args.get("ciudad") or None
    artista = request.args.get("artista") or None
    estado_pipeline = request.args.get("estado_pipeline") or None
    categoria = request.args.get("categoria") or None
    buscar = request.args.get("q") or None

    venues = database.listar_venues(
        ciudad=ciudad,
        artista=artista,
        estado_pipeline=estado_pipeline,
        categoria=categoria,
        buscar=buscar,
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
    return render_template(
        "ficha.html",
        v=venue,
        guardado=guardado,
        actividades=actividades,
        mensajes=mensajes,
        ganchos=ganchos,
        perfil_incompleto=perfil_incompleto,
        enviados_semana=database.contar_enviados_recientes(7),
        correo_ok=request.args.get("correo_ok"),
        correo_error=request.args.get("correo_error"),
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
            resumen=f"Correo enviado: {m['asunto']}",
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
