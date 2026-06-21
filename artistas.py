"""
artistas.py — Perfil de cada artista para que la IA escriba correos personalizados.

Rellenado desde los EPK (epk/Dani.pdf y epk/davikane.pdf). Edítalo cuando quieras:
afina la bio, agrega/quita links o cambia los ganchos para tus tests A/B.

Los "ganchos" son distintos ángulos de venta. Puedes generar un borrador con cada
gancho y compararlos para ver cuál conecta mejor con los venues.

No inventamos datos: todo sale del EPK.
"""

ARTISTAS = {
    "Dani": {
        "nombre_artistico": "Dani Vásquez",
        "genero": "R&B con fusión contemporánea (trap, hip-hop, drum & bass, pop, dancehall, afro, bossa nova)",
        "region": "Florida (Miami). Cantautora venezolana.",
        "estado_default": "FL",  # estado que se autocompleta en el buscador
        "idioma_correo": "en",  # 'es' español / 'en' inglés
        "bio": (
            "Dani Vásquez es una cantautora venezolana radicada en Miami que fusiona R&B "
            "con influencias contemporáneas (trap, hip-hop, drum & bass, pop, dancehall, afro y "
            "bossa nova). Compositora desde 2019 —ha escrito para Joey Montana, Leslie Shaw y "
            "Sixto Rein—, firmó con el sello Cusica Venezuela y lanzó su EP 'Sinestesia' (2023). "
            "Nominada en los Pepsi Music Awards 2023. En marzo de 2026 fue telonera de Reik en un "
            "show con sold-out en el Seminole Hard Rock Hotel & Casino de Miami. Prepara su primer "
            "álbum, 'SELAH', junto a Bragi Company."
        ),
        "links": [
            "Spotify: https://open.spotify.com/intl-es/artist/5gLCUAG9eAiT4wlqNOAIAx",
            "YouTube: https://www.youtube.com/@danivasquezmusic1",
            "Instagram: https://www.instagram.com/danivasquezofficial",
        ],
        # Brochure digital (video + dossier). Es el [LINK] de las plantillas.
        "brochure": "https://drive.google.com/drive/folders/14EZkWUxQJkEv2PKn03u1k1Sw-J6qVFJS?usp=sharing",
        # Varios ángulos para probar. El primero es el que se usa por defecto.
        "ganchos": [
            "Tracción comprobada en Miami: telonera de Reik con sold-out en el Seminole Hard Rock — arrastre real para una fecha en la zona.",
            "Artista versátil de R&B con fusiones (pop, afro, dancehall) que encaja en line-ups variados de música en vivo.",
            "Compositora con créditos (Joey Montana, Leslie Shaw) y respaldo de sello (Cusica): una artista profesional y consolidada, no emergente sin trayectoria.",
            "Lanzamiento de su álbum debut 'SELAH' (2026): momento ideal para alinear una fecha con la campaña del disco.",
        ],
        "tono": "Corporativo y formal (B2B), en inglés profesional de negocios; transmite seriedad y confianza de una empresa establecida; conciso y respetuoso.",
    },
    "Davikane": {
        "nombre_artistico": "Davikane",
        "genero": "Cumbia Texmex y regional mexicano (banda, rancheras, cumbia, mariachi)",
        "region": "Texas (todo el estado; nació en Pharr, TX, y es local/fuerte en el Valle).",
        "estado_default": "TX",  # estado que se autocompleta en el buscador
        "idioma_correo": "en",  # 'es' español / 'en' inglés
        "bio": (
            "Davikane (Victor Daniel Plasencia Flores) es un cantautor nacido en Pharr, Texas "
            "(1990), formado en saxofón y guitarra; compuso su primera balada a los 16. Tras "
            "estudiar Medicina se dedicó de lleno a la música. Su estilo fusiona Cumbia Texmex y "
            "regional mexicano (banda, rancheras, cumbia y mariachi), con influencias de Grupo "
            "Frontera, Intocable, Duelo, Carin León y Vicente Fernández. Entre sus sencillos: "
            "'Manos de Tijera', 'Señor Cantinero', 'Con un Beso' y 'Ya se me pasó'. Representado "
            "por Bragi Company."
        ),
        "links": [
            "Spotify: https://open.spotify.com/intl-es/artist/7lmoGCrvoFPByZUMgfAhG8",
            "YouTube: https://www.youtube.com/channel/UCfQx3CvqLOonBei6QdPACyg",
            "Instagram: https://www.instagram.com/davikaneoficial/",
            "TikTok: https://www.tiktok.com/@davikaneoficial",
            "Facebook: https://www.facebook.com/davikanemusic/",
        ],
        # Brochure digital (video + dossier). Es el [LINK] de las plantillas.
        "brochure": "https://drive.google.com/drive/folders/1-6sTn32ZQ_LB_r-KkVjQhS9PNOVtCUcQ?usp=sharing",
        "ganchos": [
            "Artista local del Valle: nacido en Pharr, TX — conexión natural y arrastre con el público de la región.",
            "Cumbia Texmex y regional mexicano que encaja directo con la programación de venues regionales en Texas.",
            "Catálogo de sencillos (banda, cumbia, tex-mex) listo para shows en vivo de fin de semana.",
            "Presencia en TV, radio, podcasts y redes activas: artista en crecimiento con respaldo de management profesional (Bragi Company).",
        ],
        "tono": "Corporativo y formal (B2B), en inglés profesional de negocios; transmite seriedad y confianza de una empresa establecida; conciso y respetuoso.",
    },
}


def obtener(nombre):
    """Devuelve el perfil del artista (o None si no existe)."""
    return ARTISTAS.get(nombre)
