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
import html as _html


class FaltaSendgridError(Exception):
    """No hay SENDGRID_API_KEY configurada."""


class EnvioError(Exception):
    """Error al enviar, con un mensaje claro para mostrar."""


def _cuerpo_html(cuerpo, direccion):
    """Convierte el cuerpo (texto plano) a HTML simple + pie con la dirección.
    El link de baja lo agrega SendGrid automáticamente (subscription tracking)."""
    seguro = _html.escape(cuerpo or "").replace("\n", "<br>")
    return (
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#111;line-height:1.5">'
        f"{seguro}"
        f'<hr style="border:none;border-top:1px solid #ddd;margin:20px 0">'
        f'<p style="font-size:12px;color:#888">{_html.escape(direccion)}</p>'
        f"</div>"
    )


def enviar_correo(destinatario, asunto, cuerpo):
    """
    Envía un correo. Devuelve el ID de SendGrid (string) si todo salió bien.
    Lanza FaltaSendgridError / EnvioError con mensajes claros si algo falla.
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
    )

    message = Mail(
        from_email=Email(remitente, nombre),
        to_emails=To(destinatario),
        subject=asunto,
        html_content=_cuerpo_html(cuerpo, direccion),
    )
    message.reply_to = ReplyTo(reply_to)

    # Tracking de aperturas + link de baja (CAN-SPAM).
    ts = TrackingSettings()
    ts.open_tracking = OpenTracking(True)
    ts.subscription_tracking = SubscriptionTracking(
        enable=True,
        text="Si no deseas recibir más correos, da de baja aquí: <% %>",
        html='<p style="font-size:12px;color:#888">Si no deseas recibir más correos, '
             '<a href="<% %>">da de baja aquí</a>.</p>',
    )
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
