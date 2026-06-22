# CRM + Outreach Bragi

App web local para conseguir shows: **busca venues**, **encuentra su correo**, **escribe el correo** (plantillas o IA), lo **envía**, le **hace seguimiento** y mide resultados. Operador único: Alejandro. Todo corre en tu computadora.

Fases listas: **1–6B** (buscar, enriquecer, CRM, correos por plantilla/IA, envío, cadencia de follow-ups, cola de llamada y dashboard). La nube (6C) queda **preparada** para hacerse después.

---

## Arrancar la app (lo más fácil)

**Doble clic** en el archivo **`Arrancar Bragi CRM.command`** (desde Finder).
Eso hace un respaldo de tus datos, enciende la app y abre el navegador en
**http://localhost:5001**.

- Para **apagarla:** cierra esa ventana o pulsa `Ctrl+C` en ella.
- Mientras la ventana esté abierta, la app funciona. Al cerrarla, deja de cargar (es normal).

> La primera vez que macOS abra el `.command`, puede pedir permiso: clic derecho →
> "Abrir" → "Abrir". Después ya funciona con doble clic.

### Alternativa por terminal
```bash
source venv/bin/activate
python3 app.py
```

---

## Cómo se usa (recorrido rápido)

1. **Inicio** — tablero con números: venues, enviados, % apertura/respuesta, follow-ups de hoy, cola, embudo y comparación A/B.
2. **Dani / Davikane** — desde su página, **buscar lugares** (Google Places, `$`) y **buscar correos en sus webs** en lote.
3. **Venues** — la lista con filtros. Entra a una **ficha** para ver/editar todo.
4. En la ficha: **calificar** el venue, **buscar correo en su web**, **generar el correo** (📄 plantilla = gratis · `$ ✍️ IA` = de pago), **aprobar** y **enviar** (📤).
5. **Seguimientos** — a quién le toca follow-up (día 4 / día 9). **Cola** — venues para llamar/WhatsApp.

> Los botones con **`$`** usan un servicio de pago (IA de Claude o Google Places). Las plantillas y todo lo demás son gratis.

---

## Cuidar tus datos (importante)

- Tus datos son **un solo archivo**: `bragi_crm.db`. Nunca se borra ni se recrea.
- El lanzador hace un **respaldo automático** cada vez que abres la app (carpeta `backups/`).
- Respaldo manual cuando quieras:
  ```bash
  python3 -c "import database; database.respaldar()"
  ```
- Respaldo **portátil** (JSON, sirve también para mudar a la nube luego):
  ```bash
  python3 db_tools.py export
  ```

---

## Llaves (archivo `.env`)

Las llaves van en `.env` (nunca se sube a Git):
- `GOOGLE_PLACES_API_KEY` — buscar venues (Google Places).
- `ANTHROPIC_API_KEY` — escribir correos con IA (opcional; las plantillas no la usan).
- `SENDGRID_API_KEY` y datos del remitente — enviar correos.

---

## Mapa de archivos

| Archivo | Qué hace |
|---|---|
| `app.py` | La app web (todas las pantallas). |
| `database.py` | La base de datos (SQLite) + respaldos + métricas. |
| `places_search.py` | Busca venues en Google Places. |
| `enrich.py` | Entra a la web del venue y busca correo/booking/redes (Fase 2). |
| `artistas.py` | Perfil de Dani y Davikane (bio, links, brochure, ganchos). |
| `plantillas.py` | Plantillas de correo finales (primer contacto + follow-ups). |
| `ai_email.py` | Borradores a medida con IA (opcional). |
| `email_sender.py` | Envío con SendGrid (firma + logo + dirección legal). |
| `cadencia.py` | Reglas de follow-up (día 4 / 9) y cola de llamada. |
| `db_tools.py` | Exportar/importar la base a JSON portátil. |
| `Procfile` / `requirements.txt` | Preparados para desplegar en la nube (6C). |
