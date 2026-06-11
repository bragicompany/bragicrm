"""
enrich.py — El enriquecedor (Fase 2): visita la web del venue y busca el contacto.

Para cada venue que tenga sitio web, entra a su pagina y trata de encontrar:
  - Correo de booking/contacto (prioriza enlaces mailto:, lo mas confiable).
  - Pagina de booking/contacto (link a "Contact", "Booking", "Eventos").
  - Links de redes (Instagram/Facebook...) -> SOLO se guardan para revision manual.
    NO se scrapea Instagram (va contra sus reglas); solo guardamos el enlace.

Honesto: muchos venues esconden el correo tras un formulario -> ahi no habra email,
pero si la pagina de contacto. Los venues SIN web no se pueden enriquecer asi.

USO (en la terminal):
  python3 enrich.py                 # enriquece los que aun no se han enriquecido
  python3 enrich.py --max 4         # solo 4 (para probar)
  python3 enrich.py --solo-id 6     # solo el venue con id 6
  python3 enrich.py --force         # re-enriquece aunque ya se haya hecho antes
"""

import re
import sys
import time
import argparse
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import database

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BragiCRM/1.0; investigacion de contacto para outreach)"
}

# Patron de correo. Se filtran basuras (imagenes, dominios de plantillas) mas abajo.
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Palabras que delatan una pagina de contacto/booking (en el link o su texto).
PALABRAS_CONTACTO = [
    "booking", "book-", "/book", "eventos", "events", "private-event",
    "contact", "contacto", "reserva", "reservation", "about", "nosotros",
]

# Dominios de redes sociales (solo guardamos el enlace para revisar a mano).
REDES_DOMINIOS = [
    "instagram.com", "facebook.com", "fb.com", "twitter.com", "x.com",
    "tiktok.com", "youtube.com", "linkedin.com",
]

# Correos basura que NO sirven (plantillas, imagenes, ejemplos de relleno).
EMAIL_BASURA = (
    "example.", "sentry.", "wixpress.", "godaddy", "@2x", ".png", ".jpg", ".gif",
    "@sentry", "@domain.", "yourdomain", "yoursite", "yourname", "youremail",
    "user@domain", "email@domain", "your@email", "@mysite.", "example@", "@example",
    "@email.com",
)


def es_red_social(dominio):
    """True si el dominio es una red social. Compara el dominio completo (no por substring,
    para no confundir 'dropbox.com' con 'x.com')."""
    d = dominio.lower()
    if d.startswith("www."):
        d = d[4:]
    return any(d == r or d.endswith("." + r) for r in REDES_DOMINIOS)


def obtener(url):
    """Descarga una pagina con respeto (timeout, user-agent). Devuelve (html, url_final) o (None, None)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", ""):
            return resp.text, resp.url
    except requests.RequestException:
        pass
    return None, None


def limpiar_emails(candidatos):
    """Quita correos basura y duplicados, conservando el orden."""
    vistos = []
    for e in candidatos:
        e = e.strip().strip(".").lower()
        if any(b in e for b in EMAIL_BASURA):
            continue
        if e not in vistos:
            vistos.append(e)
    return vistos


def analizar_pagina(html, base_url):
    """De una pagina saca: emails, links de contacto/booking, links de redes."""
    soup = BeautifulSoup(html, "html.parser")
    emails = []
    links_contacto = []
    redes = []

    # 1) Correos de enlaces mailto: (los mas confiables).
    for a in soup.select('a[href^="mailto:"]'):
        correo = a.get("href", "")[len("mailto:"):].split("?")[0]
        if correo:
            emails.append(correo)

    # 2) Correos sueltos en el texto/HTML.
    emails.extend(EMAIL_RE.findall(html))

    # 3) Links: clasificar en contacto/booking o redes.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        texto = (a.get_text() or "").lower()
        destino = urljoin(base_url, href)
        dominio = urlparse(destino).netloc.lower()

        if es_red_social(dominio):
            # Solo perfiles reales: descartar enlaces genericos (facebook.com sin perfil)
            # y botones de "compartir".
            ruta = urlparse(destino).path.strip("/")
            generico = ruta in ("", "share", "sharer", "sharer.php", "home")
            if ruta and not generico and "sharer" not in destino and "intent" not in destino:
                redes.append(destino)
            continue

        # Mismo sitio + palabra de contacto en la URL o en el texto del enlace.
        mismo_sitio = urlparse(destino).netloc == urlparse(base_url).netloc
        if mismo_sitio and any(p in destino.lower() or p in texto for p in PALABRAS_CONTACTO):
            links_contacto.append(destino)

    return limpiar_emails(emails), _unicos(links_contacto), _unicos(redes)


def _unicos(lista):
    """Quita duplicados conservando el orden."""
    out = []
    for x in lista:
        if x not in out:
            out.append(x)
    return out


def enriquecer_uno(venue):
    """Enriquece un venue. Devuelve un diccionario con lo encontrado (para guardar)."""
    web = venue["web"]
    nombre = venue["nombre"]
    print(f"\n→ {nombre}\n  web: {web}")

    html, url_final = obtener(web)
    if not html:
        print("  ✗ No se pudo abrir la web.")
        return {"enriquecido_el": datetime.now().isoformat(timespec="seconds")}

    emails, contacto, redes = analizar_pagina(html, url_final)

    # Visitar hasta 3 paginas de contacto/booking para buscar mas correos.
    for pagina in contacto[:3]:
        time.sleep(1)  # respeto: pausa entre paginas
        html2, url2 = obtener(pagina)
        if html2:
            e2, _, r2 = analizar_pagina(html2, url2)
            emails = _unicos(emails + e2)
            redes = _unicos(redes + r2)

    resultado = {"enriquecido_el": datetime.now().isoformat(timespec="seconds")}
    if emails:
        resultado["email"] = emails[0]  # el mejor candidato; los demas van en notas
        if len(emails) > 1:
            resultado["email"] = ", ".join(emails[:3])
    if contacto:
        resultado["pagina_booking"] = contacto[0]
    if redes:
        resultado["redes"] = " | ".join(redes[:5])

    print(f"  email:  {resultado.get('email', '— (no encontrado)')}")
    print(f"  contacto: {resultado.get('pagina_booking', '—')}")
    print(f"  redes:  {resultado.get('redes', '—')}")
    return resultado


def venues_pendientes(force=False, solo_id=None, limite=None):
    """Trae los venues con web que falta enriquecer (o todos si --force)."""
    conn = database.conectar()
    consulta = "SELECT * FROM venues WHERE web IS NOT NULL AND web != ''"
    params = []
    if solo_id:
        consulta += " AND id = ?"
        params.append(solo_id)
    elif not force:
        consulta += " AND (enriquecido_el IS NULL OR enriquecido_el = '')"
    consulta += " ORDER BY id"
    if limite:
        consulta += " LIMIT ?"
        params.append(limite)
    filas = conn.execute(consulta, params).fetchall()
    conn.close()
    return filas


def main():
    parser = argparse.ArgumentParser(description="Enriquece venues: busca correo/booking/redes en su web.")
    parser.add_argument("--max", type=int, default=None, dest="limite", help="Cuantos enriquecer (para probar)")
    parser.add_argument("--solo-id", type=int, default=None, help="Enriquecer solo el venue con este id")
    parser.add_argument("--force", action="store_true", help="Re-enriquecer aunque ya se haya hecho")
    args = parser.parse_args()

    database.crear_base()
    database.migrar()

    pendientes = venues_pendientes(force=args.force, solo_id=args.solo_id, limite=args.limite)
    if not pendientes:
        print("No hay venues con web pendientes de enriquecer. (Usa --force para repetir.)")
        return

    print(f"Enriqueciendo {len(pendientes)} venue(s)...")
    con_email = 0
    for v in pendientes:
        datos = enriquecer_uno(v)
        database.actualizar_venue(v["id"], datos)
        if datos.get("email"):
            con_email += 1
        time.sleep(1)  # respeto entre venues

    print(f"\nListo. {con_email} de {len(pendientes)} quedaron con correo.")
    print("Revisa y aprueba en la app:  http://localhost:5001")


if __name__ == "__main__":
    main()
