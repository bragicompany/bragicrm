"""
app.py — La app web del CRM (Fase 1: ver venues).

Abre dos pantallas en el navegador:
  /            -> la LISTA de venues, con filtros (ciudad, artista, estado, categoria).
  /venue/<id>  -> la FICHA de un venue (todos sus datos).

Para arrancar:   python3 app.py
Luego abre:      http://localhost:5000
"""

from urllib.parse import quote_plus

from flask import Flask, render_template, request, abort, redirect, url_for

import database

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

    return dict(enlace_google=enlace_google)


@app.route("/")
def lista():
    # Lee los filtros que vengan en la URL (vacios = sin filtro).
    ciudad = request.args.get("ciudad") or None
    artista = request.args.get("artista") or None
    estado_pipeline = request.args.get("estado_pipeline") or None
    categoria = request.args.get("categoria") or None

    venues = database.listar_venues(
        ciudad=ciudad,
        artista=artista,
        estado_pipeline=estado_pipeline,
        categoria=categoria,
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
    }

    return render_template("lista.html", venues=venues, filtros=filtros, seleccion=seleccion)


@app.route("/venue/<int:venue_id>")
def ficha(venue_id):
    venue = database.obtener_venue(venue_id)
    if venue is None:
        abort(404)
    guardado = request.args.get("guardado")  # mensaje "cambios guardados"
    return render_template("ficha.html", v=venue, guardado=guardado)


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


if __name__ == "__main__":
    # Asegura que la base exista antes de abrir la app (no borra nada).
    database.crear_base()
    # Puerto 5001: en Mac el 5000 lo ocupa AirPlay / Centro de Control.
    print("CRM Bragi corriendo en http://localhost:5001  (Ctrl+C para parar)")
    app.run(debug=True, port=5001)
