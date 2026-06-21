"""
plantillas.py — Las plantillas de correo FINALES de Bragi (v5, EN + ES).

A diferencia de ai_email.py (que le pide a Claude que escriba), aquí el texto es
FIJO: son las plantillas que Alejandro ya aprobó. La app solo rellena los huecos
con los datos del venue, así el correo sale idéntico a lo aprobado (sin riesgo de
que la IA cambie una palabra) y cumple las reglas al 100%.

Huecos que se rellenan solos:
  {saludo}  -> "Hi Maria," / "Hi The Roxy team,"  (ES: "Hola Maria," / "Hola equipo de The Roxy,")
  [venue]   -> nombre del lugar
  [LINK]    -> brochure digital del artista (campo 'brochure' en artistas.py)

Cada artista tiene: 2 idiomas (en/es) × 4 asuntos (para tests A/B) × 2 cuerpos (A/B).
La voz es de empresa ("Bragi Company"); el nombre va SOLO en la firma.
"""

import artistas

# ---------------------------------------------------------------------------
# Las plantillas (texto fijo). NO usar "corridos tumbados" ni "música propia".
# Davikane = Cumbia Texmex y regional mexicano · Dani = R&B y pop.
# ---------------------------------------------------------------------------

PLANTILLAS = {
    "Davikane": {
        "en": {
            "asuntos": [
                "a show at [venue]?",
                "a proposal for [venue]",
                "quick question",
                "booking a date at [venue]?",
            ],
            "cuerpos": {
                "A": (
                    "{saludo}\n\n"
                    "We noticed [venue] regularly hosts live music, and we think we have an "
                    "artist that fits your lineup.\n\n"
                    "We're Bragi Company, and we manage Davikane — a Cumbia Texmex and regional "
                    "mexicano artist with a show that keeps the crowd going all night. What adds "
                    "value for you: he's active in the media right now (interviews, radio, "
                    "podcasts), and he mentions the dates and venues he plays — so his show brings "
                    "extra visibility to your place too.\n\n"
                    "So it's not a shot in the dark, here's his brochure and a video of the live "
                    "show: [LINK]\n\n"
                    "If it's a fit for a date, just reply and we'll lock it in quickly — a short "
                    "call is all it takes.\n\n"
                    "Best,\nAlejandro — Bragi Company"
                ),
                "B": (
                    "{saludo}\n\n"
                    "We saw that [venue] hosts live music regularly, so we're reaching out with a "
                    "proposal for your lineup.\n\n"
                    "We're Bragi Company, and we manage Davikane (Cumbia Texmex and regional "
                    "mexicano). It's a professional, well-prepared show, ready for a date — and "
                    "he's currently getting media coverage (interviews, radio, podcasts), which "
                    "means extra visibility for your venue.\n\n"
                    "Here's his brochure and a live video so you can see the level right away: "
                    "[LINK]\n\n"
                    "If it works for you, we'll lock it in fast without taking up your time.\n\n"
                    "Best,\nAlejandro — Bragi Company"
                ),
            },
        },
        "es": {
            "asuntos": [
                "fecha para [venue]?",
                "propuesta para [venue]",
                "pregunta rápida",
                "una fecha para [venue]?",
            ],
            "cuerpos": {
                "A": (
                    "{saludo}\n\n"
                    "Vimos que en [venue] manejan música en vivo seguido, y creemos que tenemos un "
                    "artista que va perfecto para su programación.\n\n"
                    "Somos Bragi Company y manejamos a Davikane, de Cumbia Texmex y regional "
                    "mexicano, con un show que mueve al público toda la noche. Algo que les suma: "
                    "está activo en medios —entrevistas, radio y podcasts— y en cada uno menciona "
                    "las fechas y los lugares donde toca, así que su show también les trae "
                    "visibilidad a ustedes.\n\n"
                    "Para que no sea a ciegas, aquí mismo les dejamos el brochure y el video del "
                    "show en vivo: [LINK]\n\n"
                    "Si les interesa para una fecha, nos dicen y lo concretamos rápido (con una "
                    "llamada corta basta).\n\n"
                    "Un saludo,\nAlejandro — Bragi Company"
                ),
                "B": (
                    "{saludo}\n\n"
                    "Vimos que en [venue] tienen música en vivo seguido, así que les escribimos con "
                    "una propuesta para su programación.\n\n"
                    "Somos Bragi Company y manejamos a Davikane (Cumbia Texmex y regional "
                    "mexicano). Es un show profesional y bien armado, listo para una fecha, y "
                    "además está sonando en medios (entrevistas, radio, podcasts), lo que le da "
                    "visibilidad extra a su lugar.\n\n"
                    "Les dejamos el brochure y el video en vivo para que vean el nivel de una vez: "
                    "[LINK]\n\n"
                    "Si les sirve, lo concretamos rápido sin hacerles perder tiempo.\n\n"
                    "Un saludo,\nAlejandro — Bragi Company"
                ),
            },
        },
    },
    "Dani": {
        "en": {
            "asuntos": [
                "a show at [venue]?",
                "a proposal for [venue]",
                "quick question",
                "booking a date at [venue]?",
            ],
            "cuerpos": {
                "A": (
                    "{saludo}\n\n"
                    "We noticed [venue] hosts live music, and we have an artist who'd fit your "
                    "atmosphere and crowd.\n\n"
                    "We're Bragi Company, and we manage Dani Vásquez — R&B and pop, with a live "
                    "presence that draws people in. What adds value for you: she has a strong "
                    "social media following, so her show brings digital reach and buzz to your "
                    "place too.\n\n"
                    "Here's her brochure and a video of the live show: [LINK]\n\n"
                    "If it's a fit for a date, just reply and we'll lock it in quickly.\n\n"
                    "Best,\nAlejandro — Bragi Company"
                ),
                "B": (
                    "{saludo}\n\n"
                    "We saw that [venue] hosts live music, so we're reaching out with a proposal "
                    "for your lineup.\n\n"
                    "We're Bragi Company, and we manage Dani Vásquez (R&B/pop). It's a "
                    "professional, polished show, and with her social media community it brings "
                    "real reach and buzz to your venue. We'll also hand you the content from the "
                    "night, ready for your socials.\n\n"
                    "Here's her brochure and a live video: [LINK]\n\n"
                    "If it works for you, we'll lock it in fast.\n\n"
                    "Best,\nAlejandro — Bragi Company"
                ),
            },
        },
        "es": {
            "asuntos": [
                "fecha para [venue]?",
                "propuesta para [venue]",
                "pregunta rápida",
                "una fecha para [venue]?",
            ],
            "cuerpos": {
                "A": (
                    "{saludo}\n\n"
                    "Vimos que en [venue] manejan música en vivo, y tenemos una artista que conecta "
                    "con su ambiente y su público.\n\n"
                    "Somos Bragi Company y manejamos a Dani Vásquez, de R&B y pop, con una "
                    "presencia en vivo que envuelve. Algo que les suma: tiene una comunidad fuerte "
                    "en redes, así que su show también les trae alcance digital y movimiento al "
                    "lugar.\n\n"
                    "Aquí mismo les dejamos el brochure y el video del show para que lo vean: "
                    "[LINK]\n\n"
                    "Si les interesa para una fecha, nos dicen y lo concretamos rápido.\n\n"
                    "Un saludo,\nAlejandro — Bragi Company"
                ),
                "B": (
                    "{saludo}\n\n"
                    "Vimos que en [venue] tienen música en vivo, así que les escribimos con una "
                    "propuesta para su programación.\n\n"
                    "Somos Bragi Company y manejamos a Dani Vásquez (R&B/pop). Es un show "
                    "profesional y cuidado, y con su comunidad en redes les genera movimiento y "
                    "visibilidad digital. Además, les dejamos el contenido de la noche listo para "
                    "sus redes.\n\n"
                    "Les compartimos el brochure y el video en vivo: [LINK]\n\n"
                    "Si les sirve, lo concretamos rápido.\n\n"
                    "Un saludo,\nAlejandro — Bragi Company"
                ),
            },
        },
    },
}

IDIOMAS = ("en", "es")
VERSIONES = ("A", "B")
BROCHURE_PENDIENTE = "[BROCHURE PENDIENTE — agrega el link en artistas.py]"


def tiene(artista):
    """¿Hay plantillas para este artista?"""
    return artista in PLANTILLAS


def _normalizar_idioma(idioma, artista):
    """Idioma válido; si no, usa el idioma por defecto del artista (o 'en')."""
    if idioma in IDIOMAS:
        return idioma
    perfil = artistas.obtener(artista) or {}
    return perfil.get("idioma_correo", "en") if perfil.get("idioma_correo") in IDIOMAS else "en"


def asuntos(artista, idioma):
    """Lista de asuntos (con [venue] sin rellenar) para los menús de la ficha."""
    if not tiene(artista):
        return []
    idioma = _normalizar_idioma(idioma, artista)
    return list(PLANTILLAS[artista][idioma]["asuntos"])


def asuntos_por_idioma(artista):
    """Asuntos en ambos idiomas, para que la ficha cambie las opciones al vuelo (JS)."""
    if not tiene(artista):
        return {}
    return {idi: list(PLANTILLAS[artista][idi]["asuntos"]) for idi in IDIOMAS}


def brochure_de(artista):
    """Link del brochure del artista (o None si aún no está cargado)."""
    perfil = artistas.obtener(artista) or {}
    return (perfil.get("brochure") or "").strip() or None


def _saludo(idioma, encargado, venue_nombre):
    """Saludo personalizado: usa el nombre del encargado si lo hay; si no, el equipo del venue."""
    encargado = (encargado or "").strip()
    if idioma == "en":
        return f"Hi {encargado}," if encargado else f"Hi {venue_nombre} team,"
    return f"Hola {encargado}," if encargado else f"Hola equipo de {venue_nombre},"


def generar(artista, venue, idioma="en", version="A", asunto_indice=0):
    """
    Rellena la plantilla elegida con los datos del venue.

    Devuelve un dict: {asunto, cuerpo, idioma, version, asunto_variante (1..4),
    artista, brochure_falta}. 'venue' es una fila/dict con al menos 'nombre' y
    (opcional) 'encargado'.
    """
    if not tiene(artista):
        raise ValueError(f"No hay plantillas para el artista '{artista}'.")

    venue = dict(venue)
    idioma = _normalizar_idioma(idioma, artista)
    version = version if version in VERSIONES else "A"
    bloque = PLANTILLAS[artista][idioma]

    asuntos_lista = bloque["asuntos"]
    asunto_indice = max(0, min(int(asunto_indice or 0), len(asuntos_lista) - 1))

    venue_nombre = (venue.get("nombre") or "el venue").strip()
    brochure = brochure_de(artista)
    brochure_falta = brochure is None
    link = brochure or BROCHURE_PENDIENTE
    saludo = _saludo(idioma, venue.get("encargado"), venue_nombre)

    def rellenar(texto):
        return (
            texto.replace("{saludo}", saludo)
            .replace("[venue]", venue_nombre)
            .replace("[LINK]", link)
        )

    return {
        "asunto": rellenar(asuntos_lista[asunto_indice]),
        "cuerpo": rellenar(bloque["cuerpos"][version]),
        "idioma": idioma,
        "version": version,
        "asunto_variante": str(asunto_indice + 1),  # 1..4, legible para comparar
        "artista": artista,
        "brochure_falta": brochure_falta,
    }
