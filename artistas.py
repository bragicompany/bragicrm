"""
artistas.py — Perfil de cada artista para que la IA escriba correos personalizados.

EDITA ESTE ARCHIVO con la info real que vayas recopilando. Mientras más completo,
mejores correos. Lo que está entre [corchetes] son PLACEHOLDERS para que tú los llenes.

Los "ganchos" son distintos ángulos de venta. Puedes generar un borrador con cada
gancho y compararlos (tests A/B) para ver cuál conecta mejor con los venues.

No inventes datos: pon la bio y los links reales cuando los tengas.
"""

ARTISTAS = {
    "Dani": {
        "nombre_artistico": "Dani Vásquez",
        "genero": "R&B / pop / música en vivo en español",
        "region": "Florida (Miami y alrededores)",
        "idioma_correo": "es",  # 'es' español / 'en' inglés — ajusta según el venue
        "bio": "[BIO CORTA DE DANI — 2 o 3 frases: de dónde es, su estilo, logros o números relevantes (streams, shows, etc.)]",
        "links": [
            "[Link de música 1 — ej. Spotify/YouTube]",
            "[Link de música 2 — ej. Instagram/EPK]",
        ],
        # Varios ángulos para probar. El primero es el que se usa por defecto.
        "ganchos": [
            "Propuesta de show en vivo: encaja con noches de música latina en español y público joven adulto.",
            "Flexibilidad de formato: desde set acústico íntimo hasta banda completa, según el espacio del venue.",
            "Tracción/seguidores en la zona de Miami para llenar una fecha entre semana o fin de semana.",
        ],
        "tono": "cercano y profesional, en español, sin sonar a spam; breve y concreto.",
    },
    "Davikane": {
        "nombre_artistico": "Davikane",
        "genero": "regional mexicano / corridos / tex-mex",
        "region": "Texas (todo el estado; fuerte en la zona del Valle/Pharr)",
        "idioma_correo": "es",
        "bio": "[BIO CORTA DE DAVIKANE — 2 o 3 frases: de dónde es, su estilo, logros o números relevantes]",
        "links": [
            "[Link de música 1 — ej. Spotify/YouTube]",
            "[Link de música 2 — ej. Instagram/EPK]",
        ],
        "ganchos": [
            "Propuesta de show de regional mexicano/corridos para público del Valle y de Texas en general.",
            "Buen arrastre en fechas de fin de semana; ideal para venues con tarima y público de la región.",
            "Repertorio que mezcla corridos y tex-mex, adaptable a la línea de programación del venue.",
        ],
        "tono": "cercano y profesional, en español, con sabor regional; breve y directo.",
    },
}


def obtener(nombre):
    """Devuelve el perfil del artista (o None si no existe)."""
    return ARTISTAS.get(nombre)
