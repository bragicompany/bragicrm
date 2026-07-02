"""
email_sender.py — Envío de correos aprobados con SendGrid (Fase 5).

Envía desde booking@bragicompany.com (lo que esté en SENDER_EMAIL), con:
- Pie legal (dirección física de Bragi) — requisito CAN-SPAM.
- Link de baja automático (SendGrid subscription tracking) — requisito CAN-SPAM.
- Tracking de aperturas activado (los datos quedan en el panel de SendGrid).
- Reply-To a la bandeja donde Alejandro revisa las respuestas.

La llave va en .env (SENDGRID_API_KEY). Si falta, lo dice claro.
"""

import os
import re
import html as _html

# Enlaces con etiqueta estilo [texto](url) -> se convierten en enlace de texto.
_ENLACE_MD = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


class FaltaSendgridError(Exception):
    """No hay SENDGRID_API_KEY configurada."""


class EnvioError(Exception):
    """Error al enviar, con un mensaje claro para mostrar."""


def _enlace(texto, url):
    """Enlace de texto normal (no botón), para que el correo se vea personal."""
    return f'<a href="{_html.escape(url, quote=True)}">{_html.escape(texto)}</a>'


def _cuerpo_html(cuerpo, direccion, con_logo=False):
    """Convierte el cuerpo (texto plano) a HTML sencillo y PERSONAL (sin logo ni
    botones de colores), para mejorar la llegada a la bandeja Principal.
    Los enlaces [texto](url) se vuelven enlaces de texto. La dirección legal va
    al pie (CAN-SPAM); el link de baja lo agrega SendGrid (subscription tracking)."""
    # 1) Sacar los enlaces [texto](url) antes de escapar (para no romper la url) y
    #    dejar un marcador temporal en su lugar.
    enlaces = []

    def _guardar(m):
        enlaces.append(_enlace(m.group(1), m.group(2)))
        return f"\x00{len(enlaces) - 1}\x00"

    texto = _ENLACE_MD.sub(_guardar, cuerpo or "")
    # 2) Escapar el resto del texto y respetar los saltos de línea.
    seguro = _html.escape(texto).replace("\n", "<br>")
    # 3) Reinsertar los enlaces ya armados.
    for i, enl in enumerate(enlaces):
        seguro = seguro.replace(f"\x00{i}\x00", enl)
    return (
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#111;line-height:1.5">'
        f"{seguro}"
        f'<br><br><span style="font-size:12px;color:#999">{_html.escape(direccion)}</span>'
        f"</div>"
    )


def _nuevo_message_id(remitente):
    """Genera un Message-ID único y válido para este correo, del estilo
    <cadena@dominio-del-remitente>. Es el identificador que otros correos usan para
    'responder' a este y quedar en el mismo hilo."""
    import uuid
    dominio = remitente.split("@")[-1] if "@" in remitente else "bragicompany.com"
    return f"<{uuid.uuid4().hex}@{dominio}>"


def enviar_correo(destinatario, asunto, cuerpo, mensaje_id=None, in_reply_to=None):
    """
    Envía un correo. Devuelve (sg_message_id, rfc_message_id) si todo salió bien:
      - sg_message_id: el id interno de SendGrid (para el webhook de aperturas).
      - rfc_message_id: el Message-ID real del correo (para hilar los follow-ups).
    Lanza FaltaSendgridError / EnvioError con mensajes claros si algo falla.

    'mensaje_id' (opcional) se adjunta como etiqueta (custom arg) para que el
    webhook de aperturas (Fase 6C-2) pueda casar el evento con este correo exacto.

    'in_reply_to' (opcional) es el Message-ID del correo original: si viene, este
    correo se envía como respuesta a ese hilo (In-Reply-To + References), para que
    los seguimientos NO lleguen como correos nuevos.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key or "pega_aqui" in api_key:
        raise FaltaSendgridError(
            "Falta SENDGRID_API_KEY. Crea la cuenta en sendgrid.com, genera una API key "
            "y pégala en el archivo .env."
        )

    remitente = os.getenv("SENDER_EMAIL", "booking@bragicompany.com")
    nombre = os.getenv("SENDER_NAME", "Bragi Company")
    reply_to = os.getenv("REPLY_TO", remitente)
    direccion = os.getenv("BRAGI_ADDRESS", "Bragi Company, USA")

    # Acepta un correo (str) o varios (lista). Limpia vacíos y duplicados.
    if isinstance(destinatario, (list, tuple)):
        destinatarios = list(dict.fromkeys(d.strip() for d in destinatario if d and d.strip()))
    else:
        destinatarios = [destinatario.strip()] if destinatario and destinatario.strip() else []
    if not destinatarios:
        raise EnvioError("Este venue no tiene email; no se puede enviar (usa llamada/WhatsApp).")

    import sendgrid
    from sendgrid.helpers.mail import (
        Mail, Email, To, ReplyTo, TrackingSettings, OpenTracking, SubscriptionTracking,
        CustomArg, Header,
    )

    # Correo personal: sin logo ni imágenes (mejora la llegada a Principal).
    message = Mail(
        from_email=Email(remitente, nombre),
        to_emails=[To(d) for d in destinatarios],
        subject=asunto,
        html_content=_cuerpo_html(cuerpo, direccion),
    )
    message.reply_to = ReplyTo(reply_to)

    # Message-ID propio: así sabemos con qué id salió este correo y podemos hilar
    # los follow-ups después (sin depender del id que inventaría SendGrid).
    rfc_message_id = _nuevo_message_id(remitente)
    message.header = Header("Message-ID", rfc_message_id)

    # Si es un seguimiento, apunta al correo original para caer en el MISMO hilo.
    if in_reply_to:
        message.header = Header("In-Reply-To", in_reply_to)
        message.header = Header("References", in_reply_to)

    # Etiqueta para el webhook de aperturas: liga el evento a este correo (6C-2).
    if mensaje_id is not None:
        message.custom_arg = CustomArg("mensaje_id", str(mensaje_id))

    # Tracking de aperturas + link de baja (CAN-SPAM). Con subscription_tracking
    # activado, SendGrid agrega automáticamente el enlace de baja al pie del correo.
    ts = TrackingSettings()
    ts.open_tracking = OpenTracking(True)
    ts.subscription_tracking = SubscriptionTracking(enable=True)
    message.tracking_settings = ts

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        resp = sg.send(message)
    except Exception as e:
        # Mapear los errores típicos a lenguaje simple.
        texto = str(e).lower()
        codigo = getattr(e, "status_code", None)
        if codigo == 401 or "unauthorized" in texto:
            raise EnvioError("La llave de SendGrid no es válida. Revísala en .env.")
        if codigo == 403 or "forbidden" in texto or "verify" in texto or "authenticate" in texto:
            raise EnvioError(
                "SendGrid rechazó el envío: probablemente el remitente o el dominio aún "
                "no están verificados/autenticados. Completa la autenticación del dominio "
                "en SendGrid."
            )
        raise EnvioError(f"No se pudo enviar (SendGrid): {e}")

    if resp.status_code not in (200, 201, 202):
        raise EnvioError(f"SendGrid respondió con un estado inesperado ({resp.status_code}).")

    # El ID de SendGrid viene en la cabecera X-Message-Id; el rfc_message_id es el
    # que generamos arriba (para hilar los follow-ups).
    sg_id = (resp.headers.get("X-Message-Id") or "") if hasattr(resp, "headers") else ""
    return sg_id, rfc_message_id
