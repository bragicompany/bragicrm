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
import base64
import html as _html

# Enlaces con etiqueta estilo [texto](url) -> se convierten en un botón en el correo.
_ENLACE_MD = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")

# Logo que se incrusta en la firma del correo (viaja con el email).
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo_email.jpg")
LOGO_CID = "bragilogo"


class FaltaSendgridError(Exception):
    """No hay SENDGRID_API_KEY configurada."""


class EnvioError(Exception):
    """Error al enviar, con un mensaje claro para mostrar."""


def _boton(texto, url):
    """Botón lima (marca Bragi) para enlaces como el brochure."""
    return (
        f'<a href="{_html.escape(url, quote=True)}" '
        f'style="display:inline-block;background:#bef264;color:#111;text-decoration:none;'
        f'font-weight:bold;padding:11px 20px;border-radius:8px;margin:6px 0;'
        f'font-family:Arial,Helvetica,sans-serif">{_html.escape(texto)} ▸</a>'
    )


def _cuerpo_html(cuerpo, direccion, con_logo=True):
    """Convierte el cuerpo (texto plano) a HTML simple + firma con logo y dirección.
    Los enlaces con etiqueta [texto](url) se vuelven botones. El link de baja lo
    agrega SendGrid automáticamente (subscription tracking)."""
    # 1) Sacar los enlaces [texto](url) antes de escapar (para no romper la url) y
    #    dejar un marcador temporal en su lugar.
    botones = []

    def _guardar(m):
        botones.append(_boton(m.group(1), m.group(2)))
        return f"\x00{len(botones) - 1}\x00"

    texto = _ENLACE_MD.sub(_guardar, cuerpo or "")
    # 2) Escapar el resto del texto y respetar los saltos de línea.
    seguro = _html.escape(texto).replace("\n", "<br>")
    # 3) Reinsertar los botones ya armados.
    for i, btn in enumerate(botones):
        seguro = seguro.replace(f"\x00{i}\x00", btn)
    logo = (
        f'<img src="cid:{LOGO_CID}" width="120" alt="Bragi Company" '
        f'style="display:block;margin:8px 0">' if con_logo else ""
    )
    return (
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#111;line-height:1.5">'
        f"{seguro}"
        f'<hr style="border:none;border-top:1px solid #ddd;margin:20px 0">'
        f"{logo}"
        f'<p style="font-size:12px;color:#888">{_html.escape(direccion)}</p>'
        f"</div>"
    )


def enviar_correo(destinatario, asunto, cuerpo, mensaje_id=None):
    """
    Envía un correo. Devuelve el ID de SendGrid (string) si todo salió bien.
    Lanza FaltaSendgridError / EnvioError con mensajes claros si algo falla.

    'mensaje_id' (opcional) se adjunta como etiqueta (custom arg) para que el
    webhook de aperturas (Fase 6C-2) pueda casar el evento con este correo exacto.
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

    if not destinatario:
        raise EnvioError("Este venue no tiene email; no se puede enviar (usa llamada/WhatsApp).")

    import sendgrid
    from sendgrid.helpers.mail import (
        Mail, Email, To, ReplyTo, TrackingSettings, OpenTracking, SubscriptionTracking,
        Attachment, FileContent, FileName, FileType, Disposition, ContentId, CustomArg,
    )

    con_logo = os.path.exists(LOGO_PATH)
    message = Mail(
        from_email=Email(remitente, nombre),
        to_emails=To(destinatario),
        subject=asunto,
        html_content=_cuerpo_html(cuerpo, direccion, con_logo=con_logo),
    )
    message.reply_to = ReplyTo(reply_to)

    # Etiqueta para el webhook de aperturas: liga el evento a este correo (6C-2).
    if mensaje_id is not None:
        message.custom_arg = CustomArg("mensaje_id", str(mensaje_id))

    # Incrustar el logo de Bragi en la firma (imagen inline, viaja con el correo).
    if con_logo:
        with open(LOGO_PATH, "rb") as f:
            datos_logo = base64.b64encode(f.read()).decode()
        message.attachment = Attachment(
            file_content=FileContent(datos_logo),
            file_name=FileName("bragi.jpg"),
            file_type=FileType("image/jpeg"),
            disposition=Disposition("inline"),
            content_id=ContentId(LOGO_CID),
        )

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

    # El ID del mensaje viene en la cabecera X-Message-Id.
    return (resp.headers.get("X-Message-Id") or "") if hasattr(resp, "headers") else ""
