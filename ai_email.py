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


class GeneracionError(Exception):
    """Error al generar el correo, con un mensaje claro para mostrarle a Alejandro."""


def _instrucciones(en_ingles=False):
    """El 'system prompt': reglas del correo. En inglés si el correo va en inglés
    (escribir el prompt en el idioma del correo evita que el modelo lo redacte en español)."""
    if en_ingles:
        return (
            "You are the booking assistant for Bragi Company, an agency that books shows for "
            "artists. You write first-contact emails to venues and promoters proposing a concert "
            "date. Rules:\n"
            "- Professional, corporate B2B tone; honest, no spam or hype.\n"
            "- Brief: 90-150 words. Easy to read on a phone.\n"
            "- Personalize with the venue's name and city (it must not feel like a mass template).\n"
            "- Introduce the artist in 1-2 sentences using their bio and genre; include 1 link if available.\n"
            "- Use the given hook as the main angle.\n"
            "- Close with a simple call to action (would they be open to discussing a date?).\n"
            "- Sign as the Bragi Company team. Do NOT invent facts, numbers, or achievements that are "
            "not in the profile. Do NOT include a physical address or unsubscribe text (added at send time).\n"
            "- If the bio or links contain placeholders in [brackets], do NOT copy them literally: write "
            "generically and make clear naturally that those details are on the way, without inventing.\n"
            "- Write the ENTIRE email (both subject and body) in professional English.\n"
            "- Near the close, mention naturally and professionally that the Bragi team also speaks "
            "Spanish, in case they prefer to reply in Spanish "
            "(e.g., 'We're also happy to continue in Spanish if you prefer.').\n\n"
            "Respond ONLY with a valid JSON object with two keys: \"asunto\" (the subject line) and "
            "\"cuerpo\" (the email body). No text before or after, no code fences (```)."
        )
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
        "- Firma como el equipo de Bragi Company. No inventes datos, números ni logros que no "
        "estén en el perfil. No incluyas dirección física ni texto de baja (eso se añade al enviar).\n"
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


def _mensaje_usuario(venue, perfil, gancho, instruccion=None):
    """El prompt con los datos concretos de este venue y artista (en el idioma del correo)."""
    en_ingles = perfil.get("idioma_correo", "es") == "en"
    categoria = venue.get("categoria")

    if en_ingles:
        links = "\n".join(f"  - {l}" for l in perfil.get("links", [])) or "  (no links yet)"
        cat = {"A": "direct venue", "B": "promoter/intermediary"}.get(categoria, "n/a")
        extras = []
        if venue.get("genero"):
            extras.append(f"Programs genre: {venue['genero']}")
        if venue.get("web"):
            extras.append(f"Website: {venue['web']}")
        if venue.get("capacidad"):
            extras.append(f"Approx. capacity: {venue['capacidad']}")
        if venue.get("encargado"):
            extras.append(f"Contact/booker: {venue['encargado']}")
        if venue.get("notas"):
            extras.append(f"Internal notes (context only, do NOT quote verbatim): {venue['notas']}")
        extras_txt = ("\n" + "\n".join(extras)) if extras else ""
        instruccion_txt = (
            f"\n=== ADDITIONAL INSTRUCTION (follow it) ===\n{instruccion}\n" if instruccion else ""
        )
        return (
            "Write the email (subject and body) in professional English.\n\n"
            "=== VENUE ===\n"
            f"Name: {venue['nombre']}\n"
            f"City: {venue.get('ciudad') or 'n/a'}, {venue.get('estado') or ''}\n"
            f"Type: {cat}{extras_txt}\n\n"
            "=== ARTIST ===\n"
            f"Stage name: {perfil['nombre_artistico']}\n"
            f"Genre: {perfil['genero']}\n"
            f"Region: {perfil['region']}\n"
            f"Bio: {perfil['bio']}\n"
            f"Links:\n{links}\n\n"
            f"=== HOOK (main angle for this email) ===\n{gancho}\n"
            f"{instruccion_txt}\n"
            f"Desired tone: {perfil['tono']}\n\n"
            "Return a short, compelling subject line and the email body."
        )

    # --- Español ---
    links = "\n".join(f"  - {l}" for l in perfil.get("links", [])) or "  (sin links)"
    cat = {"A": "venue directo", "B": "promotor/intermediario"}.get(categoria, "s/d")
    extras = []
    if venue.get("genero"):
        extras.append(f"Género que programa: {venue['genero']}")
    if venue.get("web"):
        extras.append(f"Sitio web: {venue['web']}")
    if venue.get("capacidad"):
        extras.append(f"Capacidad aprox.: {venue['capacidad']}")
    if venue.get("encargado"):
        extras.append(f"Persona a cargo (booker): {venue['encargado']}")
    if venue.get("notas"):
        extras.append(f"Notas internas (úsalas como contexto, NO las cites textualmente): {venue['notas']}")
    extras_txt = ("\n" + "\n".join(extras)) if extras else ""
    instruccion_txt = (
        f"\n=== INSTRUCCIÓN ADICIONAL DEL USUARIO (respétala) ===\n{instruccion}\n" if instruccion else ""
    )
    return (
        "Redacta el asunto y el cuerpo en español.\n\n"
        "=== VENUE ===\n"
        f"Nombre: {venue['nombre']}\n"
        f"Ciudad: {venue.get('ciudad') or 's/d'}, {venue.get('estado') or ''}\n"
        f"Categoría: {cat}{extras_txt}\n\n"
        "=== ARTISTA ===\n"
        f"Nombre artístico: {perfil['nombre_artistico']}\n"
        f"Género: {perfil['genero']}\n"
        f"Región: {perfil['region']}\n"
        f"Bio: {perfil['bio']}\n"
        f"Links:\n{links}\n\n"
        f"=== GANCHO (ángulo principal de este correo) ===\n{gancho}\n"
        f"{instruccion_txt}\n"
        f"Tono deseado: {perfil['tono']}\n\n"
        "Devuelve un asunto corto y atractivo, y el cuerpo del correo."
    )


def _llamar_claude(system, user):
    """Hace la llamada a Claude y devuelve el texto. Traduce errores tecnicos a
    mensajes claros (GeneracionError)."""
    import anthropic  # import local: la app funciona aunque no esté instalado

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=MODELO,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError:
        raise GeneracionError("Tu llave de Anthropic no es válida. Revísala en el archivo .env.")
    except anthropic.RateLimitError:
        raise GeneracionError("Anthropic está limitando por ahora (muchas solicitudes). Espera ~1 minuto y reintenta.")
    except anthropic.APIStatusError as e:
        mensaje = (getattr(e, "message", "") or "").lower()
        tipo = (getattr(e, "type", "") or "").lower()
        if e.status_code == 403 or "billing" in tipo or "credit" in mensaje or "saldo" in mensaje:
            raise GeneracionError("La cuenta de Anthropic parece no tener saldo o permiso. Revisa el saldo en console.anthropic.com.")
        raise GeneracionError(f"La API de Anthropic devolvió un error ({e.status_code}). Intenta de nuevo en un momento.")
    except anthropic.APIConnectionError:
        raise GeneracionError("No hay conexión con Anthropic. Revisa tu internet y reintenta.")
    return next((b.text for b in resp.content if b.type == "text"), "")


def generar_borrador(venue, indice_gancho=0, instruccion=None):
    """
    Genera un borrador para un venue. 'venue' es una fila/dict con los datos.
    'indice_gancho' elige cuál de los ganchos del artista usar (para tests A/B).
    'instruccion' es una orden libre opcional ('más corto', 'más formal'...).
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
        raise GeneracionError(
            f"El venue no tiene un artista con perfil en artistas.py "
            f"(artista: '{venue.get('artista')}'). Asígnale Dani o Davikane."
        )

    ganchos = perfil.get("ganchos") or [""]
    indice_gancho = max(0, min(indice_gancho, len(ganchos) - 1))
    gancho = ganchos[indice_gancho]

    en_ingles = perfil.get("idioma_correo", "es") == "en"
    system = _instrucciones(en_ingles)
    user = _mensaje_usuario(venue, perfil, gancho, instruccion)

    # Reintenta una vez si la IA no devolvió un JSON parseable.
    for intento in range(2):
        texto = _llamar_claude(system, user)
        try:
            datos = _extraer_json(texto)
            return {
                "asunto": (datos.get("asunto") or "").strip(),
                "cuerpo": (datos.get("cuerpo") or "").strip(),
                "gancho": gancho,
                "modelo": MODELO,
            }
        except (json.JSONDecodeError, ValueError):
            continue  # un reintento más

    raise GeneracionError("La IA no devolvió el correo en el formato esperado. Vuelve a intentarlo.")
