"""
database.py — La base de datos del CRM (un solo archivo SQLite).

REGLA DE ORO: aqui viven datos reales. Este modulo NUNCA borra ni recrea la base.
- crear_base()  -> crea el archivo y la tabla SOLO si no existen (no toca lo que ya hay).
- respaldar()   -> copia el archivo de la base a la carpeta backups/ (red de seguridad).

La tabla 'venues' guarda los campos del modelo de datos del plan (seccion 9).
En la Fase 1 solo llenamos lo que entrega Google Places; el resto queda vacio
y se ira completando en fases siguientes (enriquecimiento, notas, pipeline...).
"""

import os
import sqlite3
import shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Nombre del archivo de la base (configurable en .env, con valor por defecto).
DB_FILE = os.getenv("DATABASE_FILE", "bragi_crm.db")
BACKUP_DIR = "backups"

# --- Dialecto: SQLite en local, Postgres en la nube (segun DATABASE_URL) ---
# En local no hay DATABASE_URL -> SQLite (todo igual que siempre).
# En la nube, el proveedor (Render) define DATABASE_URL -> Postgres.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DIALECTO = "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"


def es_postgres():
    return DIALECTO == "postgres"


def _traducir(sql):
    """Adapta el SQL (escrito con '?') a Postgres: escapa los '%' literales y cambia
    los marcadores '?' por '%s'. En SQLite no se llama."""
    return sql.replace("%", "%%").replace("?", "%s")


class _Conexion:
    """Envoltura fina sobre la conexion real. Permite que TODO el resto del codigo
    siga usando '?' y conn.execute(...) sin cambios: aqui se traduce a Postgres
    cuando hace falta y se delega lo demas a la conexion verdadera."""

    def __init__(self, raw, compartida=False):
        self._raw = raw
        self._compartida = compartida

    def execute(self, sql, params=()):
        if DIALECTO == "postgres":
            sql = _traducir(sql)
        return self._raw.execute(sql, params)

    def commit(self):
        return self._raw.commit()

    def close(self):
        # En modo compartido (una sola conexion por pagina) NO se cierra aqui:
        # la cierra el "teardown" del request al terminar de pintar la pagina.
        # Asi evitamos abrir y cerrar la conexion decenas de veces por carga,
        # que es lo que vuelve lenta la navegacion en Postgres/la nube.
        if not self._compartida:
            return self._raw.close()

    def cerrar_de_verdad(self):
        """Cierre real, ignorando el modo compartido (lo usa el teardown del request)."""
        return self._raw.close()

    def __getattr__(self, nombre):
        return getattr(self._raw, nombre)


def _nueva_conexion(compartida=False):
    """Abre una conexion REAL a la base (SQLite o Postgres). En ambos casos las filas
    se leen por nombre de columna (fila['columna'])."""
    if DIALECTO == "postgres":
        import psycopg
        from psycopg.rows import dict_row
        raw = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    else:
        raw = sqlite3.connect(DB_FILE)
        raw.row_factory = sqlite3.Row
    return _Conexion(raw, compartida=compartida)


def conectar():
    """Devuelve una conexion a la base.

    Dentro de una pagina web (request de Flask) REUSA una sola conexion para toda
    la carga: la primera funcion la abre y las demas la aprovechan. Esto evita abrir
    decenas de conexiones por pagina (cada una cruza la red hasta Postgres) y es la
    causa principal de la lentitud al navegar en la nube. La conexion se cierra sola
    al final del request (ver cerrar_conexion_request).

    Fuera de un request (scripts sueltos, arranque), abre una conexion normal que se
    cierra como siempre."""
    try:
        from flask import g, has_request_context
    except Exception:
        has_request_context = None

    if has_request_context and has_request_context():
        conn = g.get("_db_conn")
        if conn is None:
            conn = _nueva_conexion(compartida=True)
            g._db_conn = conn
        return conn
    return _nueva_conexion(compartida=False)


def cerrar_conexion_request(_exc=None):
    """Cierra la conexion compartida al terminar de pintar una pagina. La llama el
    teardown del request en app.py. Si no se abrio ninguna, no hace nada."""
    try:
        from flask import g
    except Exception:
        return
    conn = g.pop("_db_conn", None)
    if conn is not None:
        conn.cerrar_de_verdad()


def crear_base():
    """Crea las tablas si todavia no existen. Es seguro correrlo muchas veces.
    La llave primaria cambia segun el motor (AUTOINCREMENT en SQLite, SERIAL en Postgres)."""
    pk = "SERIAL PRIMARY KEY" if DIALECTO == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    conn = conectar()
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS venues (
            id                 {pk},
            place_id           TEXT UNIQUE,          -- id de Google Places (evita duplicados)
            nombre             TEXT NOT NULL,
            categoria          TEXT,                 -- 'A' (venue directo) / 'B' (intermediario)
            artista            TEXT,                 -- 'Dani' / 'Davikane'
            ciudad             TEXT,
            estado             TEXT,                 -- estado/provincia (TX, FL...)
            pais               TEXT,
            direccion          TEXT,
            telefono           TEXT,
            web                TEXT,
            pagina_booking     TEXT,                 -- se llena en Fase 2
            email              TEXT,                 -- se llena en Fase 2
            redes              TEXT,                 -- para revision manual (Fase 2)
            encargado          TEXT,                 -- nombre del booker (se averigua)
            capacidad          TEXT,
            genero             TEXT,
            mejor_canal        TEXT,                 -- correo / llamada / whatsapp
            estado_pipeline    TEXT DEFAULT 'nuevo', -- nuevo -> contactado -> respondio -> negociando -> cerrado/descartado
            proxima_accion     TEXT,
            recordatorio_fecha TEXT,
            notas              TEXT,
            rating             REAL,                 -- calificacion de Google (referencia)
            fuente             TEXT,                 -- de donde salio (ej: google_places)
            created_at         TEXT,
            updated_at         TEXT
        )
        """
    )
    # Tabla de actividades (linea de tiempo): un venue tiene muchas actividades.
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS actividades (
            id             {pk},
            venue_id       INTEGER NOT NULL,
            canal          TEXT,   -- llamada / whatsapp / reunion / correo / nota
            fecha          TEXT,   -- cuando paso (YYYY-MM-DD)
            resumen        TEXT,   -- que se dijo / que paso
            resultado      TEXT,   -- como resulto
            siguiente_paso TEXT,
            created_at     TEXT,
            FOREIGN KEY (venue_id) REFERENCES venues(id)
        )
        """
    )
    # Tabla de mensajes de correo (borradores de la IA). Un venue puede tener varios
    # (para probar distintos ganchos y compararlos).
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS mensajes (
            id           {pk},
            venue_id     INTEGER NOT NULL,
            asunto       TEXT,
            cuerpo       TEXT,
            estado       TEXT DEFAULT 'borrador',  -- borrador / aprobado / enviado
            gancho       TEXT,    -- que angulo se uso (para tests A/B)
            modelo       TEXT,    -- que modelo lo genero
            abierto      INTEGER DEFAULT 0,  -- 0/1 (se llena en Fase 5)
            respondido   INTEGER DEFAULT 0,  -- 0/1 (Fase 5)
            fecha_envio  TEXT,
            created_at   TEXT,
            updated_at   TEXT,
            FOREIGN KEY (venue_id) REFERENCES venues(id)
        )
        """
    )
    conn.commit()
    conn.close()
    print(f"Base de datos lista: {DB_FILE}")


def _columnas_existentes(tabla="venues"):
    """Devuelve la lista de columnas que tiene hoy una tabla (SQLite o Postgres)."""
    conn = conectar()
    if DIALECTO == "postgres":
        filas = conn.execute(
            "SELECT column_name AS name FROM information_schema.columns WHERE table_name = ?",
            (tabla,),
        ).fetchall()
    else:
        filas = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
    conn.close()
    return [f["name"] for f in filas]


def migrar():
    """Aplica cambios de estructura SIN borrar datos (solo agrega columnas que falten).

    ALTER TABLE ADD COLUMN nunca destruye filas: las filas viejas quedan con el
    campo nuevo vacio. Es seguro correrlo muchas veces.
    """
    # tabla -> [(columna, definicion)] — agregar aqui futuras columnas nuevas.
    cambios = {
        "venues": [
            ("enriquecido_el", "TEXT"),  # cuando se enriquecio (None = aun no)
        ],
        "mensajes": [
            ("sg_message_id", "TEXT"),   # id del envio en SendGrid (Fase 5)
            ("destinatario", "TEXT"),    # a quien se envio
            # --- Combinacion usada (para comparar resultados de tests A/B) ---
            ("origen", "TEXT"),          # 'plantilla' / 'ia'
            ("idioma", "TEXT"),          # 'en' / 'es'
            ("version", "TEXT"),         # 'A' / 'B' (version del cuerpo)
            ("asunto_variante", "TEXT"), # '1'..'4' (que asunto se eligio)
            ("rebote", "TEXT"),          # motivo del rebote/spam (None = entregado OK) (6C-2)
            ("rfc_message_id", "TEXT"),  # Message-ID real del correo (para hilar los follow-ups)
        ],
    }
    conn = conectar()
    aplicadas = []
    for tabla, columnas in cambios.items():
        existentes = _columnas_existentes(tabla)
        for nombre, definicion in columnas:
            if nombre not in existentes:
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}")
                aplicadas.append(f"{tabla}.{nombre}")
    conn.commit()
    conn.close()
    if aplicadas:
        print(f"Migracion: columnas agregadas -> {', '.join(aplicadas)}")
    else:
        print("Migracion: nada que aplicar (la base ya esta al dia).")
    return aplicadas


# Columnas que el usuario puede editar desde la ficha (lista blanca de seguridad).
COLUMNAS_EDITABLES = {
    "categoria", "artista", "ciudad", "estado", "pais", "direccion", "telefono",
    "web", "pagina_booking", "email", "redes", "encargado", "capacidad", "genero",
    "mejor_canal", "estado_pipeline", "proxima_accion", "recordatorio_fecha",
    "notas", "enriquecido_el",
}


def actualizar_venue(venue_id, campos):
    """Actualiza los campos indicados de un venue. Solo permite columnas de la lista blanca.

    'campos' es un diccionario {columna: valor}. Devuelve el numero de filas afectadas.
    """
    seguros = {k: v for k, v in campos.items() if k in COLUMNAS_EDITABLES}
    if not seguros:
        return 0
    seguros["updated_at"] = datetime.now().isoformat(timespec="seconds")
    asignaciones = ", ".join(f"{k} = ?" for k in seguros.keys())
    valores = list(seguros.values()) + [venue_id]
    conn = conectar()
    cur = conn.execute(f"UPDATE venues SET {asignaciones} WHERE id = ?", valores)
    conn.commit()
    afectadas = cur.rowcount
    conn.close()
    return afectadas


def respaldar():
    """Copia el archivo de la base a backups/ con la fecha y hora. 30 segundos de tranquilidad."""
    if DIALECTO == "postgres":
        # En Postgres no hay archivo local: el respaldo se hace desde el panel del
        # proveedor o con  python3 db_tools.py export  (volcado portátil).
        print("Base en Postgres: respalda desde el panel del proveedor o con db_tools export.")
        return None
    if not os.path.exists(DB_FILE):
        print("Aun no hay base que respaldar (todavia no se ha creado).")
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(BACKUP_DIR, f"{DB_FILE}.{sello}.bak")
    shutil.copy2(DB_FILE, destino)
    print(f"Respaldo creado: {destino}")
    return destino


def guardar_venue(datos):
    """
    Inserta un venue. Si el place_id ya existe, NO lo duplica (lo ignora).
    'datos' es un diccionario con las claves que correspondan a columnas de la tabla.
    Devuelve True si se inserto uno nuevo, False si ya existia.
    """
    ahora = datetime.now().isoformat(timespec="seconds")
    datos = dict(datos)  # copia para no modificar el original
    datos.setdefault("estado_pipeline", "nuevo")
    datos["created_at"] = ahora
    datos["updated_at"] = ahora

    columnas = ", ".join(datos.keys())
    marcadores = ", ".join(["?"] * len(datos))
    conn = conectar()
    if DIALECTO == "postgres":
        sql = f"INSERT INTO venues ({columnas}) VALUES ({marcadores}) ON CONFLICT (place_id) DO NOTHING"
    else:
        sql = f"INSERT OR IGNORE INTO venues ({columnas}) VALUES ({marcadores})"
    cur = conn.execute(sql, list(datos.values()))
    conn.commit()
    nuevo = cur.rowcount > 0
    conn.close()
    return nuevo


def listar_venues(ciudad=None, artista=None, estado_pipeline=None, categoria=None,
                  buscar=None, con_email=None):
    """Devuelve los venues, con filtros opcionales. Ordenados por fecha de creacion (mas nuevos primero).
    'buscar' filtra por nombre (texto parcial). 'con_email': True = solo con correo,
    False = solo sin correo, None = todos."""
    consulta = "SELECT * FROM venues WHERE 1=1"
    params = []
    if ciudad:
        consulta += " AND ciudad = ?"
        params.append(ciudad)
    if artista:
        consulta += " AND artista = ?"
        params.append(artista)
    if estado_pipeline:
        consulta += " AND estado_pipeline = ?"
        params.append(estado_pipeline)
    if categoria:
        consulta += " AND categoria = ?"
        params.append(categoria)
    if buscar:
        consulta += " AND nombre LIKE ?"
        params.append(f"%{buscar}%")
    if con_email is True:
        consulta += " AND email IS NOT NULL AND email != ''"
    elif con_email is False:
        consulta += " AND (email IS NULL OR email = '')"
    consulta += " ORDER BY created_at DESC"

    conn = conectar()
    filas = conn.execute(consulta, params).fetchall()
    conn.close()
    return filas


def obtener_venue(venue_id):
    """Devuelve un solo venue por su id (para la ficha)."""
    conn = conectar()
    fila = conn.execute("SELECT * FROM venues WHERE id = ?", (venue_id,)).fetchone()
    conn.close()
    return fila


def valores_distintos(columna):
    """Devuelve los valores unicos de una columna (para armar los filtros de la lista)."""
    columnas_validas = {"ciudad", "artista", "estado_pipeline", "categoria"}
    if columna not in columnas_validas:
        return []
    conn = conectar()
    filas = conn.execute(
        f"SELECT DISTINCT {columna} AS v FROM venues WHERE {columna} IS NOT NULL AND {columna} != '' ORDER BY {columna}"
    ).fetchall()
    conn.close()
    return [f["v"] for f in filas]


# ---------------------------------------------------------------------------
# Actividades (linea de tiempo) y recordatorios (Fase 3)
# ---------------------------------------------------------------------------

CANALES_VALIDOS = {"llamada", "whatsapp", "reunion", "correo", "nota"}


def agregar_actividad(venue_id, canal, fecha=None, resumen=None, resultado=None, siguiente_paso=None):
    """Registra una actividad en la linea de tiempo de un venue."""
    if canal not in CANALES_VALIDOS:
        canal = "nota"
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")
    conn = conectar()
    conn.execute(
        """INSERT INTO actividades (venue_id, canal, fecha, resumen, resultado, siguiente_paso, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (venue_id, canal, fecha, resumen, resultado, siguiente_paso,
         datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def listar_actividades(venue_id):
    """Devuelve las actividades de un venue, de la mas reciente a la mas antigua."""
    conn = conectar()
    filas = conn.execute(
        "SELECT * FROM actividades WHERE venue_id = ? ORDER BY fecha DESC, id DESC",
        (venue_id,),
    ).fetchall()
    conn.close()
    return filas


def eliminar_actividad(actividad_id):
    """Borra una actividad (si te equivocaste al registrarla). Devuelve su venue_id."""
    conn = conectar()
    fila = conn.execute("SELECT venue_id FROM actividades WHERE id = ?", (actividad_id,)).fetchone()
    venue_id = fila["venue_id"] if fila else None
    conn.execute("DELETE FROM actividades WHERE id = ?", (actividad_id,))
    conn.commit()
    conn.close()
    return venue_id


def listar_recordatorios():
    """Venues con recordatorio pendiente, ordenados por fecha (los mas proximos primero).
    Para la pagina Agenda."""
    conn = conectar()
    filas = conn.execute(
        """SELECT * FROM venues
           WHERE recordatorio_fecha IS NOT NULL AND recordatorio_fecha != ''
           ORDER BY recordatorio_fecha ASC"""
    ).fetchall()
    conn.close()
    return filas


# ---------------------------------------------------------------------------
# Mensajes de correo (borradores de la IA) — Fase 4
# ---------------------------------------------------------------------------

def agregar_mensaje(venue_id, asunto, cuerpo, gancho=None, modelo=None, estado="borrador",
                    origen=None, idioma=None, version=None, asunto_variante=None):
    """Guarda un borrador de correo. Devuelve el id del mensaje creado.

    origen/idioma/version/asunto_variante dejan registrada la COMBINACION usada
    (artista va en el venue) para poder comparar resultados de tests A/B despues.
    """
    ahora = datetime.now().isoformat(timespec="seconds")
    sql = """INSERT INTO mensajes
                 (venue_id, asunto, cuerpo, estado, gancho, modelo,
                  origen, idioma, version, asunto_variante, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    params = (venue_id, asunto, cuerpo, estado, gancho, modelo,
              origen, idioma, version, asunto_variante, ahora, ahora)
    conn = conectar()
    if DIALECTO == "postgres":
        cur = conn.execute(sql + " RETURNING id", params)
        nuevo_id = cur.fetchone()["id"]
    else:
        cur = conn.execute(sql, params)
        nuevo_id = cur.lastrowid
    conn.commit()
    conn.close()
    return nuevo_id


def listar_mensajes(venue_id):
    """Devuelve los mensajes de un venue, del mas reciente al mas antiguo."""
    conn = conectar()
    filas = conn.execute(
        "SELECT * FROM mensajes WHERE venue_id = ? ORDER BY created_at DESC, id DESC",
        (venue_id,),
    ).fetchall()
    conn.close()
    return filas


def obtener_mensaje(mensaje_id):
    """Devuelve un mensaje por su id."""
    conn = conectar()
    fila = conn.execute("SELECT * FROM mensajes WHERE id = ?", (mensaje_id,)).fetchone()
    conn.close()
    return fila


# Campos del mensaje que se pueden editar desde la pantalla de aprobacion.
CAMPOS_MENSAJE_EDITABLES = {"asunto", "cuerpo", "estado"}


def actualizar_mensaje(mensaje_id, campos):
    """Actualiza asunto/cuerpo/estado de un mensaje. Devuelve filas afectadas."""
    seguros = {k: v for k, v in campos.items() if k in CAMPOS_MENSAJE_EDITABLES}
    if not seguros:
        return 0
    seguros["updated_at"] = datetime.now().isoformat(timespec="seconds")
    asignaciones = ", ".join(f"{k} = ?" for k in seguros.keys())
    valores = list(seguros.values()) + [mensaje_id]
    conn = conectar()
    cur = conn.execute(f"UPDATE mensajes SET {asignaciones} WHERE id = ?", valores)
    conn.commit()
    afectadas = cur.rowcount
    conn.close()
    return afectadas


def eliminar_mensaje(mensaje_id):
    """Borra un mensaje. Devuelve su venue_id (para redirigir)."""
    conn = conectar()
    fila = conn.execute("SELECT venue_id FROM mensajes WHERE id = ?", (mensaje_id,)).fetchone()
    venue_id = fila["venue_id"] if fila else None
    conn.execute("DELETE FROM mensajes WHERE id = ?", (mensaje_id,))
    conn.commit()
    conn.close()
    return venue_id


def marcar_enviado(mensaje_id, sg_message_id, destinatario, rfc_message_id=None):
    """Marca un mensaje como enviado (Fase 5): estado, id de SendGrid, destinatario y fecha.

    'rfc_message_id' es el Message-ID real del correo (el encabezado que ven los
    clientes de correo). Se guarda para que un follow-up posterior pueda apuntar a el
    con In-Reply-To/References y asi caer en el MISMO hilo."""
    ahora = datetime.now().isoformat(timespec="seconds")
    conn = conectar()
    conn.execute(
        """UPDATE mensajes
           SET estado = 'enviado', sg_message_id = ?, destinatario = ?,
               rfc_message_id = ?, fecha_envio = ?, updated_at = ?
           WHERE id = ?""",
        (sg_message_id, destinatario, rfc_message_id, ahora, ahora, mensaje_id),
    )
    conn.commit()
    conn.close()


def hilo_message_ids(venue_id):
    """Cadena de Message-IDs de TODOS los correos ya enviados a un venue, en orden
    (del primero al ultimo): [original, F1, F2, ...]. Sirve para enganchar el proximo
    seguimiento a la cadena completa (References = toda la lista, In-Reply-To = el
    ultimo). Lista vacia si aun no hay envios con Message-ID guardado."""
    conn = conectar()
    filas = conn.execute(
        """SELECT rfc_message_id FROM mensajes
           WHERE venue_id = ? AND estado = 'enviado'
             AND rfc_message_id IS NOT NULL AND rfc_message_id != ''
           ORDER BY fecha_envio ASC, id ASC""",
        (venue_id,),
    ).fetchall()
    conn.close()
    return [f["rfc_message_id"] for f in filas]


def buscar_mensaje_por_sg(sg_message_id):
    """Encuentra el mensaje por el id de SendGrid. Los eventos del webhook traen un
    sg_message_id que EMPIEZA con el que guardamos al enviar, así que casamos por prefijo.
    Devuelve el id del mensaje o None."""
    if not sg_message_id:
        return None
    conn = conectar()
    fila = conn.execute(
        """SELECT id FROM mensajes
           WHERE sg_message_id IS NOT NULL AND sg_message_id != ''
             AND ? LIKE sg_message_id || '%'
           ORDER BY id DESC LIMIT 1""",
        (sg_message_id,),
    ).fetchone()
    conn.close()
    return fila["id"] if fila else None


def marcar_rebote(mensaje_id, motivo):
    """Marca un mensaje como rebotado (bounce/dropped/spam) con su motivo."""
    ahora = datetime.now().isoformat(timespec="seconds")
    conn = conectar()
    conn.execute(
        "UPDATE mensajes SET rebote = ?, updated_at = ? WHERE id = ?",
        ((motivo or "rebote")[:200], ahora, mensaje_id),
    )
    conn.commit()
    conn.close()


def listar_rebotes():
    """Mensajes que rebotaron, con datos del venue (para la pantalla de Rebotes)."""
    conn = conectar()
    filas = conn.execute(
        """SELECT m.id AS mensaje_id, m.destinatario, m.rebote, m.fecha_envio, m.asunto,
                  v.id AS venue_id, v.nombre, v.ciudad, v.artista, v.email, v.estado_pipeline
           FROM mensajes m
           JOIN venues v ON v.id = m.venue_id
           WHERE m.rebote IS NOT NULL AND m.rebote != ''
           ORDER BY m.fecha_envio DESC, m.id DESC"""
    ).fetchall()
    conn.close()
    return filas


def contar_rebotes():
    """Cuántos correos rebotaron (para el aviso del inicio)."""
    conn = conectar()
    fila = conn.execute(
        "SELECT COUNT(*) AS n FROM mensajes WHERE rebote IS NOT NULL AND rebote != ''"
    ).fetchone()
    conn.close()
    return fila["n"] if fila else 0


def marcar_tracking(mensaje_id, abierto=None, respondido=None):
    """Marca a mano si un correo fue abierto o respondido (mientras no hay webhook)."""
    sets, params = [], []
    if abierto is not None:
        sets.append("abierto = ?")
        params.append(1 if abierto else 0)
    if respondido is not None:
        sets.append("respondido = ?")
        params.append(1 if respondido else 0)
    if not sets:
        return
    sets.append("updated_at = ?")
    params.append(datetime.now().isoformat(timespec="seconds"))
    params.append(mensaje_id)
    conn = conectar()
    conn.execute(f"UPDATE mensajes SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    conn.close()


def contar_por(columna, tabla="venues"):
    """Cuenta filas agrupadas por una columna. Devuelve dict {valor: cantidad}."""
    columnas_ok = {"venues": {"estado_pipeline", "artista", "categoria", "ciudad"},
                   "mensajes": {"estado"}}
    if columna not in columnas_ok.get(tabla, set()):
        return {}
    conn = conectar()
    filas = conn.execute(
        f"SELECT COALESCE({columna},'(sin)') AS k, COUNT(*) AS c FROM {tabla} GROUP BY k"
    ).fetchall()
    conn.close()
    return {f["k"]: f["c"] for f in filas}


def asunto_original(venue_id):
    """Asunto del PRIMER correo enviado a un venue (no un seguimiento). Sirve para que
    el follow-up vaya en el mismo hilo: 'Re: <ese asunto>'. None si aún no hay envío."""
    conn = conectar()
    fila = conn.execute(
        """SELECT asunto FROM mensajes
           WHERE venue_id = ? AND estado = 'enviado'
             AND (origen IS NULL OR origen != 'seguimiento')
           ORDER BY fecha_envio ASC, id ASC
           LIMIT 1""",
        (venue_id,),
    ).fetchone()
    conn.close()
    return fila["asunto"] if fila else None


def venues_contactados_con_envios():
    """Venues en estado 'contactado' (ya se les escribió, aún no responden) con un
    resumen de sus correos enviados: cuántos y la fecha del último. Para la cadencia
    de follow-ups (Fase 6). No modifica nada: solo lee."""
    conn = conectar()
    filas = conn.execute(
        """
        SELECT v.*,
               SUM(CASE WHEN m.estado = 'enviado' THEN 1 ELSE 0 END) AS num_enviados,
               MAX(CASE WHEN m.estado = 'enviado' THEN m.fecha_envio END) AS ultimo_envio
        FROM venues v
        LEFT JOIN mensajes m ON m.venue_id = v.id
        WHERE v.estado_pipeline = 'contactado'
        GROUP BY v.id
        HAVING SUM(CASE WHEN m.estado = 'enviado' THEN 1 ELSE 0 END) > 0
        ORDER BY ultimo_envio ASC
        """
    ).fetchall()
    conn.close()
    return filas


def venues_calificados_sin_email():
    """Venues ya calificados (sirven) pero SIN correo: no se pueden contactar por
    email, así que van directo a gestión manual (cola de llamada)."""
    conn = conectar()
    filas = conn.execute(
        """SELECT * FROM venues
           WHERE estado_pipeline = 'calificado'
             AND (email IS NULL OR email = '')
           ORDER BY created_at DESC"""
    ).fetchall()
    conn.close()
    return filas


def metricas_correos():
    """Números de desempeño sobre los correos ENVIADOS: cuántos se abrieron y
    cuántos respondieron, con sus porcentajes. (Apertura/respuesta se marcan a mano
    por ahora; el tracking automático de SendGrid llega en la nube.)"""
    conn = conectar()
    fila = conn.execute(
        """SELECT COUNT(*) AS enviados,
                  COALESCE(SUM(abierto), 0) AS abiertos,
                  COALESCE(SUM(respondido), 0) AS respondidos
           FROM mensajes WHERE estado = 'enviado'"""
    ).fetchone()
    conn.close()
    enviados = fila["enviados"] or 0
    abiertos = fila["abiertos"] or 0
    respondidos = fila["respondidos"] or 0
    pct = lambda n: round(100 * n / enviados) if enviados else 0
    return {
        "enviados": enviados, "abiertos": abiertos, "respondidos": respondidos,
        "pct_apertura": pct(abiertos), "pct_respuesta": pct(respondidos),
    }


def comparacion_ab():
    """Compara resultados por COMBINACIÓN usada (origen · idioma · cuerpo · asunto).
    Para cada combinación: enviados, abiertos, respondidos y % de respuesta.
    Ordenado por % de respuesta (mejores primero). Solo cuenta correos enviados."""
    conn = conectar()
    filas = conn.execute(
        """SELECT COALESCE(origen, 'ia') AS origen,
                  idioma, version, asunto_variante,
                  COUNT(*) AS enviados,
                  COALESCE(SUM(abierto), 0) AS abiertos,
                  COALESCE(SUM(respondido), 0) AS respondidos
           FROM mensajes
           WHERE estado = 'enviado'
           GROUP BY origen, idioma, version, asunto_variante
           ORDER BY enviados DESC"""
    ).fetchall()
    conn.close()
    salida = []
    for f in filas:
        env = f["enviados"] or 0
        salida.append({
            "origen": f["origen"], "idioma": f["idioma"],
            "version": f["version"], "asunto_variante": f["asunto_variante"],
            "enviados": env, "abiertos": f["abiertos"], "respondidos": f["respondidos"],
            "pct_apertura": round(100 * f["abiertos"] / env) if env else 0,
            "pct_respuesta": round(100 * f["respondidos"] / env) if env else 0,
        })
    salida.sort(key=lambda r: (r["pct_respuesta"], r["enviados"]), reverse=True)
    return salida


def contar_enviados_hoy():
    """Cuántos correos se han enviado HOY (para no pasarte de la rampa diaria)."""
    hoy = datetime.now().strftime("%Y-%m-%d")
    conn = conectar()
    fila = conn.execute(
        "SELECT COUNT(*) AS n FROM mensajes WHERE estado = 'enviado' AND substr(fecha_envio,1,10) = ?",
        (hoy,),
    ).fetchone()
    conn.close()
    return fila["n"] if fila else 0


def contar_enviados_recientes(dias=7):
    """Cuántos correos se han enviado en los últimos N días (para vigilar la rampa)."""
    corte = (datetime.now() - timedelta(days=dias)).isoformat(timespec="seconds")
    conn = conectar()
    fila = conn.execute(
        "SELECT COUNT(*) AS n FROM mensajes WHERE estado = 'enviado' AND fecha_envio >= ?",
        (corte,),
    ).fetchone()
    conn.close()
    return fila["n"] if fila else 0


if __name__ == "__main__":
    # Si corres  python3 database.py  directamente, crea la base.
    crear_base()
