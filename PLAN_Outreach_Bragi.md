# PLAN DE PROYECTO — CRM + OUTREACH DE BRAGI
### Documento de planeación (Fase 2, después del sitio web)

> **Cómo usar este documento:** Es la planeación completa, ANTES de escribir código. Cuando abras Claude Code, sube este archivo como primer mensaje y di: *"Este es el plan del proyecto que quiero construir. Léelo y ayúdame a empezar por la Fase 1."* Con eso, Claude Code tendrá todo el contexto.
>
> **Estado actual:** planeación. No se ha escrito código todavía.

---

## 1. EL OBJETIVO EN UNA FRASE

Construir un **CRM con outreach integrado** (app web Python/Flask, **un solo usuario: Alejandro**) para conseguir **shows para Dani Vásquez (Florida) y Davikane (Texas)**, partiendo de cero en contactos: encuentra venues/promotores, arma una ficha de cada uno, propone un correo personalizado con IA, y —**tras la aprobación de Alejandro**— lo envía y le hace seguimiento. Si no responden, el contacto cae solo en una cola para gestionarlo por **llamada / WhatsApp / visita**. Todo el historial de cada venue vive en su ficha.

**El norte:** generar ventas de conciertos. Todo lo demás (scraping, IA, dashboard) es medio, no fin.

---

## 2. DECISIONES YA TOMADAS (no se rediscuten)

- [x] **Es un CRM**, no un simple enviador de correos: el centro es la base de contactos con su estado e historial.
- [x] **Enfoque semiautomático.** La app *busca y propone*; Alejandro *revisa y aprueba* antes de enviar. Nada se envía solo.
- [x] **Operador único: Alejandro.** Sin sistema de usuarios/roles/permisos.
- [x] **Gestión multicanal:** correo, llamada, WhatsApp y reuniones/visitas — todo se registra en la ficha.
- [x] **Cadencia correo-primero:** el correo es el toque automático; llamada/WhatsApp/visita entran solo si no responden.
- [x] **Correo `@bragicompany.com` se compra ANTES de arrancar el outreach.** Prerrequisito (ver §10).
- [x] **Dos artistas a la vez:** Dani (Florida) y Davikane (Texas).
- [x] **Claude no ejecuta compras ni acciones en cuentas del usuario.** Alejandro hace cuentas/compras; Claude guía y escribe el código.
- [x] **Arranque simple y local;** a la nube solo lo que necesita estar siempre encendido; costo cerca de $0 al inicio.

---

## 3. OBJETIVOS Y MÉTRICAS

**Volumen recomendado (rampa, no "cuántos más mejor"):**
- Semanas 1–2: ~10 venues nuevos/semana (mientras se "calienta" el dominio de correo).
- Semana 3 en adelante: subir gradual hasta ~25–40/semana.
- Razón: un dominio nuevo que envía mucho de golpe cae en spam y se quema. El calentamiento gradual es obligatorio (ver §10).

**Métricas en el panel:**
- [ ] Venues contactados (semana / acumulado) y por canal.
- [ ] Tasa de apertura y de respuesta del correo.
- [ ] Contactos en cola de llamada / WhatsApp.
- [ ] Conversaciones activas (negociando).
- [ ] **Shows cerrados** ← la métrica que importa.

**Meta inicial sugerida (ajustable):** en 3 meses, abrir conversación real con 10–15 venues/promotores y cerrar 1–3 shows.

---

## 4. PERFIL DEL OBJETIVO (a quién le escribimos)

### Categoría A — Venues directos (cierras 1 show por contacto)
- Bares y restaurantes grandes **con tarima** para shows medianos/grandes.
- Salas de conciertos. Clubes.

### Categoría B — Intermediarios (un contacto = muchos shows) ⭐
- Promotores de eventos. Empresas de eventos.
- *Prioritarios: un buen promotor abre varias fechas.*

### "Venue ideal" por artista (a afinar)
- **Davikane (TX):** regional mexicano / corridos / tex-mex; ciudades de Texas (grandes + zona del Valle/Pharr, donde es local).
- **Dani (FL):** R&B / pop / música en vivo en español; Miami y alrededores.
- Filtros por lugar: ciudad, capacidad aprox., ¿tiene tarima?, ¿programa el género?, ¿tiene web/booking?

---

## 5. EL CRM: VISTAS Y FICHA DE CONTACTO  ⭐ (corazón del sistema)

### Vista de lista (tu tablero de contactos)
Tabla con todos los venues y, de un vistazo: nombre, ciudad, categoría (A/B), artista objetivo y **estado en el pipeline**. Con **filtros**: por ciudad, por artista, por estado, por canal. Ej.: "venues de Texas que ya respondieron pero no he cerrado", o "contactos en cola de llamada".

**Pipeline (estados):** `nuevo → contactado → respondió → negociando → cerrado / descartado`
(+ marca especial: `sin respuesta → cola de llamada`).

### Ficha individual (al hacer clic en un contacto)
Todo lo de ese venue en un solo lugar:
- **Datos del lugar:** nombre, dirección, ciudad, capacidad aprox., género que programa.
- **Sitio web** (link directo) + página de booking/contacto encontrada.
- **Teléfono** (de Google Places) → para la llamada en frío.
- **Email de booking** (si se encontró) y **redes** (para investigar a mano).
- **Encargado / booker:** nombre de la persona a cargo (se va llenando al averiguar).
- **Mejor forma de contacto** (correo / llamada / WhatsApp).
- **Línea de tiempo de actividad** (ver §6): todos los correos, llamadas, WhatsApp y reuniones.
- **Notas libres** de Alejandro.
- **Próxima acción + recordatorio** ("llamar el martes").

---

## 6. GESTIÓN MULTICANAL Y CADENCIA

**Cuatro canales, todos registrados en la ficha:**
- ✉️ **Correo** — el único **automatizado** (lo envía la app vía SendGrid, tras tu aprobación).
- 📞 **Llamada** — manual (tú llamas desde tu teléfono); la app te da el número y registras el resultado.
- 💬 **WhatsApp** — manual (la app te da un link `wa.me`; registras la conversación).
- 🤝 **Reunión / visita** — manual; agendas y registras.

> **Importante (honestidad técnica):** la app **no marca, no llama ni escribe WhatsApp por ti** (eso es terreno legal y de costos delicado). Para esos canales es tu **copiloto**: te da el contacto, la ficha y el lugar para registrar cómo te fue.

**La cadencia (correo primero, luego escalar):**
```
Día 0   → Correo personalizado (aprobado por ti)
Día ~4  → Follow-up correo 1   (si no respondió)
Día ~9  → Follow-up correo 2   (si no respondió)
Sin respuesta tras la secuencia → el contacto cae solo en la COLA DE LLAMADA
        → tú llamas / mandas WhatsApp / agendas visita, y registras
```
La app te muestra la cola de llamada y los recordatorios; tú no tienes que acordarte de nada. *(Cantidad de follow-ups y días: ajustables.)*

---

## 7. FLUJO DE TRABAJO (el ciclo que construimos)

```
1. BUSCAR     → app busca venues por ciudad/género (Google Places) → "candidatos"
2. ENRIQUECER → app entra a la web del venue, busca booking/contacto y redes → arma ficha
3. APROBAR #1 → Alejandro revisa la ficha y decide si califica
4. GENERAR    → IA redacta un correo personalizado (borrador) según artista + categoría
5. APROBAR #2 → Alejandro revisa/edita el borrador
6. ENVIAR     → SendGrid envía desde @bragicompany.com
7. SEGUIR     → la app rastrea aperturas/respuestas; dispara follow-ups (con tu OK)
8. ESCALAR    → si no responde, pasa a la cola de llamada/WhatsApp/visita (manual)
```
Tu trabajo: pasos 3 y 5 (decidir y aprobar) + la gestión manual del paso 8. Lo pesado lo hace la app.

---

## 8. ARQUITECTURA TÉCNICA

- **Lenguaje/framework:** Python + Flask.
- **Desarrollo:** Claude Code en el computador de Alejandro. Código local con **Git**.
- **Scraping + IA:** **local**, por tandas/manual al inicio (no necesita 24/7 → costo $0).
- **Dashboard + tracking + follow-ups:** nube (**Railway o Render**, plan gratis/barato, despliegue desde Git).
- **Base de datos:** SQLite para empezar; migrar a Postgres al subir el dashboard.
- **Envío de correo:** SendGrid + dominio `@bragicompany.com`.

---

## 9. MODELO DE DATOS (qué guardamos)

- **contactos (venues/promotores):** nombre, categoría (A/B), ciudad, estado/país, capacidad aprox., género, web, página de booking, teléfono, email, redes, **encargado/booker**, **mejor canal**, artista objetivo, estado del pipeline, próxima acción + fecha de recordatorio, notas.
- **actividades (línea de tiempo):** contacto, **canal** (correo/llamada/whatsapp/reunión), fecha, resumen/qué se dijo, resultado, siguiente paso.
- **mensajes (correo):** asunto, cuerpo, estado (borrador/aprobado/enviado), fecha, abierto (s/n), respondido (s/n).
- **seguimientos/recordatorios:** qué toca, cuándo, hecho/pendiente.

Política de datos: guardar solo lo necesario; poder borrar un contacto y marcar **"no volver a contactar"**.

---

## 10. ENTREGABILIDAD DE CORREO (que NO caiga en spam)

- [ ] Comprar/activar correo `@bragicompany.com`.
- [ ] Autenticar el dominio: **SPF, DKIM y DMARC** (SendGrid guía el proceso; Hostinger permite poner esos registros DNS).
- [ ] **Calentar el dominio:** pocos correos/día subiendo gradual (rampa de §3).
- [ ] Respetar **límites diarios**.
- [ ] Cada correo: identificación de Bragi, **dirección física** y forma de **darse de baja** (requisito legal, §11).
- [ ] **Respuestas** llegan a una bandeja que Alejandro revisa; marcar "no contactar" a quien lo pida.

---

## 11. LEGAL Y ÉTICA (los límites)

- [ ] **CAN-SPAM (EE.UU.):** sin asuntos engañosos, identificar la oferta, dirección física, opción de baja respetada.
- [ ] **Términos de plataformas:** Google Places vía su API (ok). **Instagram NO se scrapea** (va contra sus términos y bloquea la cuenta) → redes solo para investigación **manual**.
- [ ] **Fuentes realistas de contacto:** (1) web del venue (booking/contacto) = lo más confiable; (2) teléfono (Google Places); (3) redes a mano.
- [ ] **Canales manuales (llamada/WhatsApp/visita):** los hace Alejandro en persona; respetar horarios y no acosar.
- [ ] **Tono honesto, sin spam**, coherente con la marca ("industria limpia").

---

## 12. CONEXIONES / CUENTAS / APIs (checklist)

> Alejandro crea cuentas y obtiene llaves; el código las usa. Las llaves van en `.env`, **nunca** en el código ni en Git.

- [ ] **Google Cloud — Places API** → buscar venues (nombre, dirección, teléfono, web). *No entrega correos.* Configurar límites.
- [ ] **SendGrid** → envío + tracking de aperturas. Plan gratis.
- [ ] **Correo `@bragicompany.com`** (Hostinger) → dirección de envío (§10).
- [ ] **Railway o Render** → alojar el dashboard. Plan gratis/barato. (Alternativas: PythonAnywhere, o Python de Hostinger Business.)
- [ ] **Git / GitHub** → versionado y respaldo.
- [ ] **Cuenta de Claude Code** (§14).
- [ ] **Secretos:** `.env` local + variables de entorno en la nube; `.gitignore` que excluya `.env`.

---

## 13. CHECKLIST DE PRERREQUISITOS (antes de abrir Claude Code)

- [ ] Correo `@bragicompany.com` comprado y funcionando.
- [ ] Google Cloud + Places API activada + llave + límites configurados.
- [ ] Cuenta SendGrid creada.
- [ ] Cuenta Railway/Render creada (puede esperar al despliegue).
- [ ] Cuenta GitHub creada.
- [ ] Cuenta de Claude Code lista (§14).
- [ ] Primeras ciudades definidas (TX para Davikane, FL para Dani).
- [ ] A la mano: bios cortas, links de música y 1–2 "ganchos" por artista (para que la IA escriba mejor).

---

## 14. EXIGENCIAS DE CLAUDE CODE (para que trabaje bien)

*(Verificado en la documentación oficial — https://code.claude.com/docs/en/setup)*

**Requisitos del sistema:**
- **SO:** macOS, Windows (se recomienda WSL) o Linux.
- **Cuenta de pago de Claude:** Claude Code **requiere** suscripción de pago (Pro, Max, Team o Enterprise) **o** cuenta de Anthropic Console con créditos de API. **El plan gratis de Claude.ai no incluye Claude Code.**
- **RAM:** 4 GB mínimo (8 GB recomendado).
- **Internet** + terminal (Bash, Zsh, PowerShell o CMD). *(También hay app de escritorio para macOS/Windows si no quieres terminal.)*

**Instalación (la hace Alejandro):**
- Recomendado — **instalador nativo** (sin Node.js): Mac `curl -fsSL https://claude.ai/install.sh | bash`; Windows PowerShell `irm https://claude.ai/install.ps1 | iex`. También `brew install claude-code`.
- Alternativo — npm (requiere **Node.js 18+**): `npm install -g @anthropic-ai/claude-code`.
- **Recomendación para este proyecto:** instalar **Node.js 18+ igual**, porque muchos servidores MCP y utilidades del ecosistema lo necesitan (vía `npx`).
- Instalar **Git** (2.23+) y configurar usuario/email.

**Lo que Claude Code necesita del proyecto:**
- [ ] Un **`CLAUDE.md`** en la raíz del repo con el contexto (lo derivamos de este plan); es lo primero que lee.
- [ ] Repo con **Git** inicializado (commits frecuentes = poder deshacer).
- [ ] Llaves en **`.env`** + `.gitignore`; nunca en el código.
- [ ] Instrucciones por **fases** (§15), no "hazlo todo de una".

---

## 15. FASES DE CONSTRUCCIÓN (MVP primero)

- **Fase 0 — Preparación:** instalar Claude Code, Node, Git; crear cuentas (§13); repo + `CLAUDE.md`.
- **Fase 1 — Buscar + CRM base:** Google Places → guardar venues → **vista de lista + ficha** para verlos.
- **Fase 2 — Enriquecer + aprobar:** web del venue → booking/contacto → ficha completa; pantalla de Aprobación #1.
- **Fase 3 — Registro multicanal:** línea de tiempo de actividades + notas + encargado + recordatorios (ya puedes gestionar llamadas/WhatsApp/visitas a mano, aunque el correo aún no esté).
- **Fase 4 — Correos con IA:** borradores personalizados; pantalla de Aprobación #2.
- **Fase 5 — Enviar + tracking:** SendGrid; registrar aperturas/respuestas.
- **Fase 6 — Cadencia + cola de llamada + dashboard:** follow-ups, escalado a cola de llamada, métricas; desplegar dashboard en la nube.
- **Fase 7 — Afinar:** mejorar plantillas según lo que responde, ampliar ciudades.

> **MVP que ya da valor:** Fases 1–5 (buscar → ver en CRM → aprobar → gestionar a mano → generar y enviar correo).

---

## 16. RIESGOS Y MITIGACIONES

- **Correos a spam** → autenticar dominio + calentamiento + volumen bajo (§10).
- **Bloqueo por scraping** → no scrapear Instagram; API de Google + webs públicas (§11).
- **Costos disparados** → límites en Google Cloud; planes gratis; correr local.
- **Contactos de baja calidad** → la aprobación #1 filtra antes de gastar un envío.
- **Llaves filtradas** → `.env` + `.gitignore`.
- **Perder el hilo con muchos contactos** → para eso es el CRM: línea de tiempo + recordatorios.

---

## 17. LO QUE QUEDA POR DECIDIR

- [ ] Ciudades concretas de arranque (TX y FL).
- [ ] Dirección física para los correos (requisito legal) — ¿la sede de Bragi?
- [ ] ¿A qué bandeja llegan las respuestas? (idealmente `@bragicompany.com`).
- [ ] Texto base / tono de los correos por artista (lo redactamos antes de la Fase 4).
- [x] Cadencia: **correo primero**, follow-ups, y llamada/WhatsApp/visita si no responden. *(Días sugeridos: 0, 4, 9 → luego cola de llamada. Ajustables.)*

---

## 18. EVOLUCIONAR EL CRM SIN PERDER DATOS

El CRM está pensado para **crecer contigo**: vas a poder agregarle mejoras a medida que descubras necesidades, sin perder la información ya recogida. La clave es entender que el sistema tiene dos partes que viven aparte:

- **El código** (pantallas, botones, lógica) → se cambia y mejora libremente.
- **La base de datos** (contactos, notas, llamadas, historial) → es tu información acumulada y se mantiene intacta.

Mejorar el CRM = tocar el **código**, y eso **no borra la base de datos** (son archivos distintos).

### Dos tipos de mejora
- **No tocan los datos (la mayoría, 100% seguras):** agregar pantallas, reportes, filtros, botones, un canal nuevo, cambiar el diseño. La información sigue intacta.
- **Cambian la estructura de los datos:** p. ej. agregar un campo nuevo a cada contacto ("presupuesto", "fecha tentativa"). También se hace **sin perder nada** (los contactos viejos quedan con ese campo vacío hasta llenarlo), pero requiere una **migración**: decirle a la base "agrega esta columna". Claude Code sabe hacerlo; no se improvisa sobre datos reales.

### Regla de oro: respaldar antes de cambios estructurales
- La base es **un solo archivo** (SQLite). Respaldarla = **copiar ese archivo** a otra carpeta o a Google Drive. 30 segundos.
- **Hábito obligatorio:** copia la base **antes** de cualquier cambio que toque su estructura. Si algo sale mal, restauras la copia y listo.
- Dos redes de seguridad: **Git** protege el *código* (puedes volver a una versión anterior); el **respaldo del archivo** protege los *datos*. Juntas te dejan experimentar tranquilo.

### Flujo sano para cada mejora
1. Se te ocurre la mejora usando el CRM.
2. Se la pides a Claude Code **avisando que hay datos reales que no se deben perder**.
3. Si toca la estructura → **respaldas la base** (copias el archivo).
4. Claude Code aplica el cambio (con migración si hace falta).
5. Pruebas: si todo bien, sigues; si falla, restauras el respaldo.

### Regla permanente en `CLAUDE.md`
Esto queda escrito en el `CLAUDE.md` para que Claude Code lo respete en cada sesión:
> *"Hay datos reales en uso. Nunca borrar ni recrear la base de datos. Ante cambios de estructura: usar migraciones y recordarle a Alejandro respaldar el archivo de la base antes de aplicar."*

---

*Documento de planeación — CRM + outreach de Bragi Company. Operador único: Alejandro. Semiautomático con aprobación humana. Multicanal (correo automático; llamada/WhatsApp/visita manuales). Construir por fases; MVP = Fases 1–5. El CRM evoluciona sin perder datos: respaldo + migración antes de cambios estructurales.*
