"""
ai_email.py — Genera borradores de correo personalizados con Claude (Fase 4).

Toma los datos de un venue + el perfil del artista (artistas.py) y le pide a Claude
un asunto y un cuerpo. NO envía nada: solo redacta el borrador para que Alejandro
lo revise y apruebe (la pantalla de Aprobación #2).

El modelo es Claude Opus 4.8 vía el SDK oficial `anthropic`. La llave va en .env
(ANTHROPIC_API_KEY). Cada borrador cuesta fracciones de centavo.
"""

import os
import json

import artistas

MODELO = "claude-opus-4-8"


class FaltaLlaveError(Exception):
    """Se lanza cuando no hay ANTHROPIC_API_KEY configurada."""


def _instrucciones():
    """El 'system prompt': quién es Claude aquí y las reglas del correo."""
    return (
        "Eres el asistente de booking de Bragi Company, una agencia que consigue shows "
        "para artistas. Escribes correos de PRIMER contacto a venues y promotores para "
        "proponer una fecha de concierto. Reglas:\n"
        "- Tono honesto y profesional, nada de spam ni exageraciones.\n"
        "- Breve: 90-150 palabras. Fácil de leer en el teléfono.\n"
        "- Personaliza con el nombre y la ciudad del venue (no suene a plantilla masiva).\n"
        "- Presenta al artista en 1-2 frases usando su bio y género; incluye 1 link si hay.\n"
        "- Usa el gancho indicado como ángulo principal.\n"
        "- Cierra con una llamada a la acción simple (¿les interesa que hablemos de una fecha?).\n"
        "- Firma como 'El equipo de Bragi Company'. No inventes datos, números ni logros "
        "que no estén en el perfil. No incluyas dirección física ni texto de baja "
        "(eso se añade al enviar).\n"
        "- Si la bio o los links vienen con placeholders entre [corchetes], NO los copies "
        "literalmente: escribe de forma genérica y deja claro de manera natural que faltan "
        "esos detalles, sin inventar.\n\n"
        "Responde ÚNICAMENTE con un objeto JSON válido con dos claves: \"asunto\" y "
        "\"cuerpo\". Sin texto antes ni después, sin comillas de código (```)."
    )


def _extraer_json(texto):
    """Saca el objeto JSON de la respuesta, aunque venga con ``` o texto extra."""
    t = texto.strip()
    if t.startswith("```"):
        # quitar la primera y última línea de cerca de código
        t = t.split("```", 2)[1] if t.count("```") >= 2 else t.strip("`")
        if t.lstrip().startswith("json"):
            t = t.lstrip()[4:]
    inicio, fin = t.find("{"), t.rfind("}")
    if inicio != -1 and fin != -1:
        t = t[inicio:fin + 1]
    return json.loads(t)


def _mensaje_usuario(venue, perfil, gancho):
    """El prompt con los datos concretos de este venue y artista."""
    idioma = "español" if perfil.get("idioma_correo", "es") == "es" else "inglés"
    links = "\n".join(f"  - {l}" for l in perfil.get("links", [])) or "  (sin links)"
    return (
        f"Escribe el correo en {idioma}.\n\n"
        f"=== VENUE ===\n"
        f"Nombre: {venue['nombre']}\n"
        f"Ciudad: {venue.get('ciudad') or 's/d'}, {venue.get('estado') or ''}\n"
        f"Categoría: {'venue directo' if venue.get('categoria') == 'A' else 'promotor/intermediario' if venue.get('categoria') == 'B' else 's/d'}\n\n"
        f"=== ARTISTA ===\n"
        f"Nombre artístico: {perfil['nombre_artistico']}\n"
        f"Género: {perfil['genero']}\n"
        f"Región: {perfil['region']}\n"
        f"Bio: {perfil['bio']}\n"
        f"Links:\n{links}\n\n"
        f"=== GANCHO (ángulo principal de este correo) ===\n{gancho}\n\n"
        f"Tono deseado: {perfil['tono']}\n\n"
        f"Devuelve un asunto corto y atractivo, y el cuerpo del correo."
    )


def generar_borrador(venue, indice_gancho=0):
    """
    Genera un borrador para un venue. 'venue' es una fila/dict con los datos.
    'indice_gancho' elige cuál de los ganchos del artista usar (para tests A/B).
    Devuelve un dict: {asunto, cuerpo, gancho, modelo}.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise FaltaLlaveError(
            "Falta ANTHROPIC_API_KEY. Pega tu llave de Anthropic en el archivo .env "
            "(la obtienes en console.anthropic.com)."
        )

    venue = dict(venue)  # acepta tanto filas de SQLite como diccionarios
    perfil = artistas.obtener(venue.get("artista"))
    if not perfil:
        raise ValueError(f"No hay perfil para el artista '{artista}' en artistas.py")

    ganchos = perfil.get("ganchos") or [""]
    indice_gancho = max(0, min(indice_gancho, len(ganchos) - 1))
    gancho = ganchos[indice_gancho]

    # Import aquí para que el resto de la app funcione aunque 'anthropic' no esté instalado.
    import anthropic

    client = anthropic.Anthropic()
    respuesta = client.messages.create(
        model=MODELO,
        max_tokens=2000,
        system=_instrucciones(),
        messages=[{"role": "user", "content": _mensaje_usuario(venue, perfil, gancho)}],
    )
    texto = next((b.text for b in respuesta.content if b.type == "text"), "")
    datos = _extraer_json(texto)
    return {
        "asunto": datos.get("asunto", "").strip(),
        "cuerpo": datos.get("cuerpo", "").strip(),
        "gancho": gancho,
        "modelo": MODELO,
    }
