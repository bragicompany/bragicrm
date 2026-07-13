"""
evaluar.py — El filtro de ENCAJE (fit): puntúa cada venue según qué tan bien le
late al género y público del artista, y pre-califica el pipeline. (Fase 7)

¿Para qué? Que en el CRM te queden contactos perfilados —los que sí encajan con
Dani o Davikane— en vez de un cajón revuelto. Deja de tirar venues a mano.

CÓMO FUNCIONA (semiautomático, tú apruebas):
  - Toma el texto de la web del venue (que ya bajamos al enriquecer) + el tipo y
    resumen de Google, y el perfil del artista (géneros AFINES e INCOMPATIBLES).
  - Le pide a Claude Haiku 4.5 (rápido y barato para clasificar) un puntaje 0-100,
    el género detectado, si es compatible (sí / no / incierto) y un motivo de una línea.
  - Rutea el pipeline de forma CONSERVADORA:
      · compatible = "no"  -> descartado (con motivo)  [solo si es claramente otro género]
      · compatible = "sí" y puntaje >= 65 -> calificado
      · en cualquier otro caso -> se queda en 'nuevo' para que TÚ lo revises
  - Nada se contacta solo. El auto-descarte es reversible (botón "reabrir").

REGLA DE ORO (encaje): NO descartar por dudar. Solo se descarta cuando el género
es clara e inequívocamente incompatible (ej.: venue de puro rock noventero para
Davikane). Géneros parecidos o que podrían encajar -> se conservan para revisión.

USO (en la terminal):
  python3 evaluar.py --dry-run            # muestra puntajes SIN escribir en la base (para revisar)
  python3 evaluar.py --dry-run --max 6    # solo 6 (prueba rápida)
  python3 evaluar.py                      # evalúa y GUARDA (rutea el pipeline)
  python3 evaluar.py --solo-id 12         # solo un venue
  python3 evaluar.py --incluir-todos      # también re-evalúa calificado/descartado (por defecto solo 'nuevo')
"""

import os
import sys
import json
import argparse
from datetime import datetime

from bs4 import BeautifulSoup
from dotenv import load_dotenv

import artistas
import database
import enrich  # reutilizamos su descarga de la web (obtener)
import ai_email  # reutilizamos su extractor de JSON robusto (_extraer_json)

load_dotenv()

# Haiku 4.5: rápido y barato, perfecto para CLASIFICAR en volumen. Los correos
# siguen con Opus (ai_email.py). Cada evaluación cuesta fracciones de centavo.
MODELO_FIT = "claude-haiku-4-5"

# Umbrales de ruteo (ajustables tras ver resultados reales).
UMBRAL_CALIFICA = 65


class EvaluacionError(Exception):
    """Error al evaluar, con mensaje claro para mostrar."""


def _texto_web(venue, limite=3500):
    """Baja la web del venue y devuelve un fragmento de texto visible (para leer el
    género que anuncian, el calendario, etc.). Vacío si no tiene web o no abre."""
    web = venue.get("web")
    if not web:
        return ""
    html, _ = enrich.obtener(web)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for basura in soup(["script", "style", "noscript"]):
        basura.decompose()
    texto = " ".join(soup.get_text(separator=" ").split())
    return texto[:limite]


def _instrucciones():
    """El 'system prompt': reglas del evaluador. Conservador con el descarte."""
    return (
        "Eres un analista de booking de Bragi Company. Tu trabajo es decidir si un "
        "venue (bar, restaurante, salón, club, promotor) ENCAJA con el género y el "
        "público de un artista, para no perder tiempo ofreciéndoselo a lugares que "
        "tocan música totalmente distinta.\n\n"
        "Devuelve:\n"
        "- fit_score: 0-100. Qué tan bien le late el venue al artista (100 = encaje perfecto).\n"
        "- genero_detectado: qué género(s) parece programar el venue (o 'desconocido').\n"
        "- compatible: 'si' / 'no' / 'incierto'.\n"
        "- motivo: UNA línea corta explicando el puntaje (en español).\n\n"
        "REGLAS PARA 'compatible' (MUY IMPORTANTE, sé CONSERVADOR):\n"
        "- 'no' SOLO cuando el género del venue es CLARA e INEQUÍVOCAMENTE incompatible "
        "con el artista (ej.: venue de puro rock de los 90 para un artista de regional "
        "mexicano). Úsalo solo cuando estés seguro.\n"
        "- 'si' cuando el género encaja o es PARECIDO / adyacente (podría encajar). Ante "
        "géneros afines, di 'si'.\n"
        "- 'incierto' cuando no hay señal suficiente del género, la info es vaga, o dudas. "
        "NUNCA pongas 'no' por dudar: si dudas, es 'incierto'.\n"
        "- Un lugar genérico de música en vivo variada, o del que no sabes el género, NO es "
        "incompatible: es 'incierto' o 'si'.\n\n"
        "No inventes datos que no estén en la info del venue.\n\n"
        "Responde ÚNICAMENTE con un objeto JSON válido con estas claves: "
        "\"fit_score\" (entero 0-100), \"genero_detectado\" (texto), "
        "\"compatible\" (\"si\" | \"no\" | \"incierto\") y \"motivo\" (texto, una línea). "
        "Sin texto antes ni después, sin comillas de código (```)."
    )


def _mensaje_usuario(venue, perfil, usar_web=True):
    """El prompt con los datos concretos de este venue y artista.
    usar_web=False evita bajar la web (más rápido; para el filtro al buscar,
    donde nos apoyamos en el nombre + tipo/resumen de Google)."""
    afines = ", ".join(perfil.get("generos_afines", [])) or "(sin lista)"
    incompat = ", ".join(perfil.get("generos_incompatibles", [])) or "(sin lista)"
    web_txt = _texto_web(venue) if usar_web else ""
    señales = []
    if venue.get("tipos_google"):
        señales.append(f"Tipos (Google): {venue['tipos_google']}")
    if venue.get("resumen_google"):
        señales.append(f"Resumen (Google): {venue['resumen_google']}")
    if venue.get("rating"):
        señales.append(f"Rating Google: {venue['rating']}")
    if usar_web:
        señales.append(f"Texto de su web: {web_txt or '(sin web o no se pudo abrir)'}")
    señales_txt = "\n".join(señales)

    return (
        "=== ARTISTA ===\n"
        f"Nombre: {perfil['nombre_artistico']}\n"
        f"Género: {perfil['genero']}\n"
        f"Géneros AFINES (encaja o podría encajar -> compatible 'si'): {afines}\n"
        f"Géneros INCOMPATIBLES (claramente otro público -> 'no' solo si es claro): {incompat}\n\n"
        "=== VENUE A EVALUAR ===\n"
        f"Nombre: {venue['nombre']}\n"
        f"Ciudad: {venue.get('ciudad') or 's/d'}, {venue.get('estado') or ''}\n"
        f"Categoría: {'venue directo' if venue.get('categoria') == 'A' else 'promotor/intermediario' if venue.get('categoria') == 'B' else 's/d'}\n"
        f"{señales_txt}\n\n"
        "Evalúa el encaje siguiendo las reglas. Responde SOLO el JSON pedido."
    )


def _llamar_claude(system, user):
    """Llama a Claude Haiku 4.5 con salida en JSON forzada. Traduce errores a mensajes claros."""
    import anthropic  # import local: la app funciona aunque no esté instalado

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=MODELO_FIT,
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError:
        raise EvaluacionError("Tu llave de Anthropic no es válida. Revísala en el .env.")
    except anthropic.RateLimitError:
        raise EvaluacionError("Anthropic está limitando (muchas solicitudes). Espera ~1 min.")
    except anthropic.APIStatusError as e:
        raise EvaluacionError(f"La API de Anthropic devolvió un error ({e.status_code}).")
    except anthropic.APIConnectionError:
        raise EvaluacionError("No hay conexión con Anthropic. Revisa tu internet.")
    texto = next((b.text for b in resp.content if b.type == "text"), "")
    return ai_email._extraer_json(texto)  # tolera ``` y texto extra alrededor del JSON


def evaluar_uno(venue, usar_web=True):
    """Evalúa el encaje de un venue. Devuelve dict con fit_score, genero_detectado,
    compatible, motivo y el estado_pipeline sugerido. NO escribe en la base.
    usar_web=False no baja la web (más rápido; para el filtro automático al buscar)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise EvaluacionError("Falta ANTHROPIC_API_KEY en el .env.")
    venue = dict(venue)
    perfil = artistas.obtener(venue.get("artista"))
    if not perfil:
        raise EvaluacionError(
            f"El venue no tiene artista con perfil (artista: '{venue.get('artista')}')."
        )
    datos = _llamar_claude(_instrucciones(), _mensaje_usuario(venue, perfil, usar_web))
    score = max(0, min(100, int(datos.get("fit_score", 0))))
    compatible = (datos.get("compatible") or "incierto").lower()

    # Ruteo conservador: solo se descarta si la IA dice claramente "no".
    if compatible == "no":
        sugerido = "descartado"
    elif compatible == "si" and score >= UMBRAL_CALIFICA:
        sugerido = "calificado"
    else:
        sugerido = "nuevo"  # revisar a mano

    return {
        "fit_score": score,
        "genero_detectado": datos.get("genero_detectado", "desconocido"),
        "compatible": compatible,
        "motivo": (datos.get("motivo") or "").strip(),
        "estado_sugerido": sugerido,
    }


def evaluar_y_guardar(venue, usar_web=True):
    """Evalúa un venue y GUARDA el resultado: puntaje, motivo, género detectado y
    el estado_pipeline ruteado. Devuelve el dict de la evaluación.

    Se usa para el filtro automático al BUSCAR venues nuevos. OJO: solo se debe
    llamar sobre venues recién creados; NUNCA re-clasifica los que ya tienes."""
    r = evaluar_uno(venue, usar_web=usar_web)
    database.actualizar_venue(venue["id"], {
        "fit_score": r["fit_score"],
        "fit_motivo": r["motivo"],
        "genero": r["genero_detectado"],
        "fit_evaluado_el": datetime.now().isoformat(timespec="seconds"),
        "estado_pipeline": r["estado_sugerido"],
    })
    return r


def filtrar_nuevos(venues, usar_web=False):
    """Filtro automático para una tanda de venues RECIÉN buscados: evalúa y rutea
    cada uno. Tolera fallos (si uno truena, sigue con los demás). Por defecto NO baja
    la web (rápido, se apoya en nombre + tipo/resumen de Google). Devuelve conteos."""
    conteo = {"calificado": 0, "descartado": 0, "nuevo": 0, "errores": 0}
    for v in venues:
        try:
            r = evaluar_y_guardar(v, usar_web=usar_web)
            conteo[r["estado_sugerido"]] = conteo.get(r["estado_sugerido"], 0) + 1
        except Exception:
            conteo["errores"] += 1  # el venue queda 'nuevo' sin puntaje; se revisa a mano
    return conteo


def venues_a_evaluar(force=False, solo_id=None, incluir_todos=False, limite=None):
    """Trae los venues a evaluar. Por defecto solo los 'nuevo' sin evaluar (la cola
    de triage). No toca lo que ya contactaste ni lo que ya clasificaste a mano."""
    conn = database.conectar()
    consulta = "SELECT * FROM venues WHERE 1=1"
    params = []
    if solo_id:
        consulta += " AND id = ?"
        params.append(solo_id)
    else:
        if incluir_todos:
            consulta += " AND estado_pipeline IN ('nuevo', 'calificado', 'descartado')"
        else:
            consulta += " AND estado_pipeline = 'nuevo'"
        if not force:
            consulta += " AND (fit_evaluado_el IS NULL OR fit_evaluado_el = '')"
    consulta += " ORDER BY id"
    if limite:
        consulta += " LIMIT ?"
        params.append(limite)
    filas = conn.execute(consulta, params).fetchall()
    conn.close()
    return filas


def _linea(venue, r):
    """Una línea de resumen para la terminal."""
    flecha = {"calificado": "✅ CALIFICA", "descartado": "❌ DESCARTA", "nuevo": "🔍 REVISAR"}
    return (
        f"[{r['fit_score']:>3}] {flecha.get(r['estado_sugerido'], '?')}  "
        f"{venue['nombre'][:38]:38}  ({venue.get('ciudad') or '?'}/{venue.get('artista')})\n"
        f"        género: {r['genero_detectado']} · compatible: {r['compatible']}\n"
        f"        {r['motivo']}"
    )


def main():
    parser = argparse.ArgumentParser(description="Evalúa el encaje (fit) de los venues con el artista.")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra; NO escribe en la base.")
    parser.add_argument("--max", type=int, default=None, dest="limite", help="Cuántos evaluar (para probar).")
    parser.add_argument("--solo-id", type=int, default=None, help="Evaluar solo este venue.")
    parser.add_argument("--incluir-todos", action="store_true", help="También calificado/descartado (def: solo 'nuevo').")
    parser.add_argument("--force", action="store_true", help="Re-evaluar aunque ya se haya evaluado.")
    args = parser.parse_args()

    pendientes = venues_a_evaluar(
        force=args.force, solo_id=args.solo_id,
        incluir_todos=args.incluir_todos, limite=args.limite,
    )
    if not pendientes:
        print("No hay venues pendientes de evaluar. (Usa --force o --incluir-todos.)")
        return

    modo = "DRY-RUN (no escribe)" if args.dry_run else "ESCRIBIENDO en la base"
    print(f"Evaluando encaje de {len(pendientes)} venue(s) con {MODELO_FIT}. Modo: {modo}\n")

    conteo = {"calificado": 0, "descartado": 0, "nuevo": 0}
    for v in pendientes:
        try:
            r = evaluar_uno(v)
        except EvaluacionError as e:
            print(f"  ✗ {v['nombre'][:38]}: {e}")
            continue
        print(_linea(v, r))
        conteo[r["estado_sugerido"]] = conteo.get(r["estado_sugerido"], 0) + 1

        if not args.dry_run:
            campos = {
                "fit_score": r["fit_score"],
                "fit_motivo": r["motivo"],
                "genero": r["genero_detectado"],
                "fit_evaluado_el": datetime.now().isoformat(timespec="seconds"),
                "estado_pipeline": r["estado_sugerido"],
            }
            database.actualizar_venue(v["id"], campos)
        print()

    print(f"\nResumen: ✅ {conteo['calificado']} califican · "
          f"🔍 {conteo['nuevo']} a revisar · ❌ {conteo['descartado']} descartar.")
    if args.dry_run:
        print("Fue DRY-RUN: no se escribió nada. Quita --dry-run para guardar y rutear el pipeline.")


if __name__ == "__main__":
    main()
