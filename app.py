"""
app.py — La app web del CRM (Fase 1: ver venues).

Abre dos pantallas en el navegador:
  /            -> la LISTA de venues, con filtros (ciudad, artista, estado, categoria).
  /venue/<id>  -> la FICHA de un venue (todos sus datos).

Para arrancar:   python3 app.py
Luego abre:      http://localhost:5000
"""

from flask import Flask, render_template, request, abort

import database

app = Flask(__name__)


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
    return render_template("ficha.html", v=venue)


if __name__ == "__main__":
    # Asegura que la base exista antes de abrir la app (no borra nada).
    database.crear_base()
    print("CRM Bragi corriendo en http://localhost:5000  (Ctrl+C para parar)")
    app.run(debug=True, port=5000)
