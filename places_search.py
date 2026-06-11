"""
places_search.py — El buscador de venues (Google Places API nueva).

Lo corres TU a mano, por tandas. Le das una busqueda en texto y a quien pertenece,
y guarda los resultados en la base. Google Places da: nombre, direccion, telefono,
web, ciudad, rating. NO da correos (eso es la Fase 2).

EJEMPLOS DE USO (en la terminal):

  python3 places_search.py --query "salas de conciertos en Pharr, TX" \
      --artista Davikane --categoria A --ciudad Pharr --estado TX

  python3 places_search.py --query "promotores de eventos en Miami, FL" \
      --artista Dani --categoria B --ciudad Miami --estado FL

Notas:
- --categoria A = venue directo, B = intermediario/promotor.
- --max controla cuantos resultados traer (por defecto 20, maximo util ~60).
- Si un lugar ya estaba guardado, NO se duplica.
"""

import os
import sys
import time
import argparse
import requests
from dotenv import load_dotenv

import database

load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

# Le pedimos a Google solo los campos que usamos (asi cuesta menos y va mas rapido).
CAMPOS = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.nationalPhoneNumber,"
    "places.internationalPhoneNumber,"
    "places.websiteUri,"
    "places.rating,"
    "places.addressComponents,"
    "nextPageToken"
)


def _ciudad_de_componentes(componentes):
    """Intenta sacar la ciudad de los 'addressComponents' que devuelve Google."""
    if not componentes:
        return None
    # 'locality' suele ser la ciudad; si no, probamos con otros niveles.
    prioridad = ["locality", "postal_town", "administrative_area_level_2"]
    for tipo in prioridad:
        for comp in componentes:
            if tipo in comp.get("types", []):
                return comp.get("longText")
    return None


def buscar(query, max_resultados=20):
    """Llama a Google Places y devuelve una lista de lugares (manejando paginacion)."""
    if not API_KEY:
        print("ERROR: falta GOOGLE_PLACES_API_KEY. Copia .env.example a .env y pega tu llave.")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": CAMPOS,
    }

    lugares = []
    page_token = None

    while len(lugares) < max_resultados:
        cuerpo = {"textQuery": query, "pageSize": 20}
        if page_token:
            cuerpo["pageToken"] = page_token

        resp = requests.post(ENDPOINT, headers=headers, json=cuerpo, timeout=30)
        if resp.status_code != 200:
            print(f"ERROR de Google Places ({resp.status_code}): {resp.text}")
            break

        data = resp.json()
        lugares.extend(data.get("places", []))

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        # Google pide una pausa breve antes de usar el token de la siguiente pagina.
        time.sleep(2)

    return lugares[:max_resultados]


def ejecutar(query, artista, categoria, ciudad, estado, pais, max_resultados):
    """Busca y guarda en la base. Imprime un resumen claro."""
    # Asegura que la base y la tabla existan (no borra nada si ya estan).
    database.crear_base()

    print(f"\nBuscando en Google Places: \"{query}\" ...")
    lugares = buscar(query, max_resultados)
    print(f"Google devolvio {len(lugares)} lugares.\n")

    nuevos = 0
    repetidos = 0
    for lugar in lugares:
        nombre = (lugar.get("displayName") or {}).get("text")
        if not nombre:
            continue

        datos = {
            "place_id": lugar.get("id"),
            "nombre": nombre,
            "categoria": categoria,
            "artista": artista,
            "ciudad": ciudad or _ciudad_de_componentes(lugar.get("addressComponents")),
            "estado": estado,
            "pais": pais,
            "direccion": lugar.get("formattedAddress"),
            "telefono": lugar.get("nationalPhoneNumber") or lugar.get("internationalPhoneNumber"),
            "web": lugar.get("websiteUri"),
            "rating": lugar.get("rating"),
            "fuente": "google_places",
        }

        if database.guardar_venue(datos):
            nuevos += 1
            print(f"  + Guardado: {nombre}")
        else:
            repetidos += 1
            print(f"  . Ya existia: {nombre}")

    print(f"\nResumen: {nuevos} nuevos, {repetidos} ya estaban. Total recibidos: {len(lugares)}.")
    print("Abre la app web para verlos:  python3 app.py\n")


def main():
    parser = argparse.ArgumentParser(
        description="Busca venues en Google Places y los guarda en el CRM."
    )
    parser.add_argument("--query", required=True, help="Que buscar, ej: 'salas de conciertos en Pharr, TX'")
    parser.add_argument("--artista", required=True, choices=["Dani", "Davikane"], help="A quien apunta este venue")
    parser.add_argument("--categoria", required=True, choices=["A", "B"], help="A=venue directo, B=intermediario/promotor")
    parser.add_argument("--ciudad", default=None, help="Ciudad (si no, se intenta deducir de la direccion)")
    parser.add_argument("--estado", default=None, help="Estado, ej: TX o FL")
    parser.add_argument("--pais", default="USA", help="Pais (por defecto USA)")
    parser.add_argument("--max", type=int, default=20, dest="max_resultados", help="Cuantos resultados traer (def. 20)")
    args = parser.parse_args()

    ejecutar(
        query=args.query,
        artista=args.artista,
        categoria=args.categoria,
        ciudad=args.ciudad,
        estado=args.estado,
        pais=args.pais,
        max_resultados=args.max_resultados,
    )


if __name__ == "__main__":
    main()
