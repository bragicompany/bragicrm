"""
cadencia.py — La cadencia de seguimiento (Fase 6A).

Regla simple, correo-primero (del plan):
  día 0  -> primer correo
  día 4  -> follow-up 1   (si no respondió)
  día 9  -> follow-up 2   (si sigue sin responder)
  después -> CAJA DE LLAMADA (gestión manual: llamada/WhatsApp/visita)

Todo se CALCULA a partir de lo que ya hay en la base (correos enviados + estado
del venue). No agrega columnas ni cambia datos: solo lee y clasifica.

- Un venue "en cadencia" es el que está en estado 'contactado' (ya se le escribió,
  aún no responde). Si responde, la app lo mueve a 'respondió' y sale de aquí.
"""

from datetime import date, datetime

import database

# Espaciado entre correos, en días desde el ÚLTIMO enviado.
GAP_POR_NUMERO = {1: 4, 2: 5}  # tras el 1er correo: +4 (día 4); tras el 2do: +5 (≈día 9)
MAX_CORREOS = 3                 # día 0, 4 y 9 -> 3 correos; agotados, va a la cola


def _a_fecha(valor):
    """Convierte 'YYYY-MM-DD' o ISO con hora a date. Devuelve None si no se puede."""
    if not valor:
        return None
    texto = str(valor)[:10]
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return None


def clasificar(num_enviados, ultimo_envio, hoy=None):
    """Dice en qué punto de la cadencia está un venue contactado.

    Devuelve un dict:
      - cat: 'toca' (ya toca follow-up) | 'esperando' (aún no) | 'cola' (a llamada)
      - numero: qué follow-up sería (2 = el segundo correo, etc.)
      - dias: días desde el último correo
      - faltan: días que faltan para el próximo follow-up (si 'esperando')
    """
    hoy = hoy or date.today()
    num_enviados = int(num_enviados or 0)
    if num_enviados <= 0:
        return None
    if num_enviados >= MAX_CORREOS:
        return {"cat": "cola", "motivo": "Agotó los 3 correos sin respuesta", "dias": None}

    fecha_ultimo = _a_fecha(ultimo_envio)
    dias = (hoy - fecha_ultimo).days if fecha_ultimo else None
    gap = GAP_POR_NUMERO.get(num_enviados, 5)
    # follow-up que toca: #1 tras el 1er correo, #2 tras el 2do (1 ó 2).
    follow = num_enviados

    if dias is None:
        return {"cat": "esperando", "follow": follow, "dias": None, "faltan": gap}
    if dias >= gap:
        return {"cat": "toca", "follow": follow, "dias": dias}
    return {"cat": "esperando", "follow": follow, "dias": dias, "faltan": gap - dias}


def seguimientos(hoy=None):
    """Arma las dos listas de la pantalla de seguimiento:
       - 'toca': venues a los que hoy les toca un follow-up (orden: más atrasados primero).
       - 'esperando': contactados que aún no toca (con cuántos días faltan).
    Cada item es (venue_row, info_clasificacion)."""
    hoy = hoy or date.today()
    toca, esperando = [], []
    for v in database.venues_contactados_con_envios():
        info = clasificar(v["num_enviados"], v["ultimo_envio"], hoy)
        if not info:
            continue
        if info["cat"] == "toca":
            toca.append((v, info))
        elif info["cat"] == "esperando":
            esperando.append((v, info))
    toca.sort(key=lambda par: par[1].get("dias") or 0, reverse=True)
    esperando.sort(key=lambda par: par[1].get("faltan") or 0)
    return toca, esperando


def cola_llamada(hoy=None):
    """Arma la cola de gestión manual (llamada/WhatsApp/visita). Dos motivos:
       1) 'Agotó los 3 correos sin respuesta'  (cadencia terminada)
       2) 'Calificado pero sin correo'         (no se puede escribir email)
    Cada item es (venue_row, motivo)."""
    hoy = hoy or date.today()
    cola = []
    for v in database.venues_contactados_con_envios():
        info = clasificar(v["num_enviados"], v["ultimo_envio"], hoy)
        if info and info["cat"] == "cola":
            cola.append((v, info["motivo"]))
    for v in database.venues_calificados_sin_email():
        cola.append((v, "Calificado pero sin correo — contáctalo por teléfono/WhatsApp"))
    return cola


def conteos(hoy=None):
    """Números para el panel de inicio: cuántos follow-ups tocan hoy y cola de llamada."""
    hoy = hoy or date.today()
    toca, _ = seguimientos(hoy)
    return {"toca": len(toca), "cola": len(cola_llamada(hoy))}
