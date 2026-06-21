# CLAUDE.md — Proyecto CRM + Outreach de Bragi Company

> Este archivo es el contexto permanente del proyecto. Léelo al inicio de cada sesión.
> El plan completo está en `PLAN_Outreach_Bragi.md` (en esta misma carpeta) — consúltalo para el detalle.

---

## QUÉ ESTAMOS CONSTRUYENDO

Un **CRM con outreach integrado** para conseguir shows (conciertos) para dos artistas:
- **Dani Vásquez** — R&B/pop — enfoque en **Florida** (Miami).
- **Davikane** — regional mexicano/corridos — enfoque en **Texas** (incl. zona del Valle/Pharr).

La app busca venues y promotores, arma una ficha de cada uno, propone un correo personalizado, y —tras la aprobación del usuario— lo envía y le hace seguimiento. Si no responden, el contacto pasa a una cola para gestión manual por llamada/WhatsApp/visita.

**El norte es generar ventas de conciertos.** Todo lo demás es medio, no fin.

---

## QUIÉN LO USA

- **Operador único: Alejandro.** NO construir sistema de usuarios, roles ni permisos. Es una app de una sola persona.

---

## PRINCIPIOS DE TRABAJO (IMPORTANTE)

1. **Construir por FASES, no todo de una.** Ver la lista de fases abajo. Terminar y probar una fase antes de seguir.
2. **Antes de escribir código nuevo, explica tu plan y espera el visto bueno de Alejandro.** Resume qué vas a crear y por qué.
3. **Enfoque semiautomático:** la app *busca y propone*; Alejandro *revisa y aprueba* antes de enviar nada. Nada se envía solo.
4. **Explica en lenguaje simple.** Alejandro es de marketing, no programador. Evita jerga innecesaria; cuando uses un término técnico, explícalo en una línea.
5. **Commits frecuentes con Git** para poder deshacer.

---

## REGLA DE ORO: NO PERDER DATOS

- Habrá **datos reales** (contactos, notas, historial) en uso.
- **NUNCA borrar ni recrear la base de datos.**
- Ante cambios de estructura: **usar migraciones** y **recordarle a Alejandro respaldar el archivo de la base** (copiar el archivo SQLite) ANTES de aplicar.
- El código y los datos viven aparte: cambiar el código no debe tocar los datos.

---

## SEGURIDAD

- Las API keys y secretos van en un archivo **`.env`** (variables de entorno), **NUNCA escritos en el código**.
- Crear y mantener un **`.gitignore`** que excluya `.env` y la base de datos, para que no se suban a Git.
- Si necesitas una llave que no está, pídesela a Alejandro; no la inventes.

---

## STACK TÉCNICO

- **Lenguaje/framework:** Python + Flask.
- **Base de datos:** SQLite al inicio (un archivo local). Migrar a Postgres cuando se despliegue el dashboard en la nube.
- **Búsqueda de venues:** Google Places API (la llave la tiene Alejandro, va en `.env`). *Nota: Places NO entrega correos.*
- **Enriquecimiento de contacto:** entrar a la web del venue para encontrar página de booking/contacto. **NO scrapear Instagram** (va contra sus términos); las redes son solo para investigación manual.
- **Envío de correo:** SendGrid (se integra en la Fase 5) desde `booking@bragicompany.com`.
- **Nube (más adelante):** Railway o Render para el dashboard/seguimiento.
- **Versionado:** Git.

---

## CONTACTOS OBJETIVO (dos categorías)

- **Categoría A — Venues directos:** bares/restaurantes grandes con tarima, salas de conciertos, clubes. (1 show por contacto.)
- **Categoría B — Intermediarios:** promotores y empresas de eventos. ⭐ Prioritarios (un contacto puede abrir varias fechas).

---

## CANALES Y CADENCIA

- **Canales registrables en cada ficha:** correo (automático), llamada, WhatsApp, reunión/visita (estos 3 manuales — la app es copiloto, NO marca ni escribe por el usuario).
- **Cadencia correo-primero:** correo → follow-ups (sugerido días 0, 4, 9) → si no responde, el contacto cae en una **cola de llamada** para gestión manual.
- **Volumen:** rampa para no quemar el dominio — empezar ~10/semana e ir subiendo a ~25–40/semana.

---

## EL CRM (corazón del sistema)

- **Vista de lista** con filtros (ciudad, artista, estado, canal) y el estado de cada contacto en el pipeline:
  `nuevo → contactado → respondió → negociando → cerrado / descartado` (+ marca `sin respuesta → cola de llamada`).
- **Ficha individual** por contacto: datos del lugar, sitio web, página de booking, teléfono, email, redes (para revisión manual), encargado/booker, mejor canal, línea de tiempo de actividad (correos/llamadas/WhatsApp/reuniones), notas libres, próxima acción + recordatorio.

---

## FASES DE CONSTRUCCIÓN

- **Fase 1 — Buscar + CRM base:** Google Places → guardar venues en SQLite → vista de lista + ficha para verlos. ← EMPEZAR AQUÍ
- **Fase 2 — Enriquecer + aprobar:** web del venue → booking/contacto → ficha completa; pantalla de aprobación #1.
- **Fase 3 — Registro multicanal:** línea de tiempo de actividad + notas + encargado + recordatorios (gestión manual de llamadas/WhatsApp/visitas).
- **Fase 4 — Correos con IA:** borradores personalizados por artista/categoría; pantalla de aprobación #2.
- **Fase 5 — Enviar + tracking:** integrar SendGrid + autenticación del dominio; enviar aprobados; registrar aperturas/respuestas.
- **Fase 6 — Cadencia + cola de llamada + dashboard:** follow-ups, escalado a cola de llamada, métricas; desplegar en la nube.
- **Fase 7 — Afinar:** mejorar plantillas según resultados, ampliar ciudades.

**MVP que ya da valor: Fases 1–5.**

---

## ESTADO ACTUAL

- Cuentas listas: Google Cloud + Places API (con llave), correo `booking@bragicompany.com`.
- Pendientes: SendGrid (Fase 5), GitHub, despliegue en nube (más adelante).
- **Próximo paso: Fase 1.**

---

## DECISIONES QUE QUEDAN POR DEFINIR (no bloquean la Fase 1)

- Ciudades concretas de arranque (TX y FL).
- Dirección física para los correos (requisito legal CAN-SPAM).
- Tono/plantillas de correo por artista (se definen antes de la Fase 4).
