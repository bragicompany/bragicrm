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
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Nombre del archivo de la base (configurable en .env, con valor por defecto).
DB_FILE = os.getenv("DATABASE_FILE", "bragi_crm.db")
BACKUP_DIR = "backups"


def conectar():
    """Abre una conexion a la base. row_factory permite leer filas por nombre de columna."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def crear_base():
    """Crea la tabla 'venues' si todavia no existe. Es seguro correrlo muchas veces."""
    conn = conectar()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS venues (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
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
    conn.commit()
    conn.close()
    print(f"Base de datos lista: {DB_FILE}")


def _columnas_existentes():
    """Devuelve la lista de columnas que tiene hoy la tabla venues."""
    conn = conectar()
    filas = conn.execute("PRAGMA table_info(venues)").fetchall()
    conn.close()
    return [f["name"] for f in filas]


def migrar():
    """Aplica cambios de estructura SIN borrar datos (solo agrega columnas que falten).

    ALTER TABLE ADD COLUMN nunca destruye filas: los venues viejos quedan con el
    campo nuevo vacio. Es seguro correrlo muchas veces.
    """
    existentes = _columnas_existentes()
    # (columna, definicion) — agregar aqui futuras columnas nuevas.
    nuevas = [
        ("enriquecido_el", "TEXT"),  # cuando se enriquecio (None = aun no)
    ]
    conn = conectar()
    aplicadas = []
    for nombre, definicion in nuevas:
        if nombre not in existentes:
            conn.execute(f"ALTER TABLE venues ADD COLUMN {nombre} {definicion}")
            aplicadas.append(nombre)
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
    cur = conn.execute(
        f"INSERT OR IGNORE INTO venues ({columnas}) VALUES ({marcadores})",
        list(datos.values()),
    )
    conn.commit()
    nuevo = cur.rowcount > 0
    conn.close()
    return nuevo


def listar_venues(ciudad=None, artista=None, estado_pipeline=None, categoria=None):
    """Devuelve los venues, con filtros opcionales. Ordenados por fecha de creacion (mas nuevos primero)."""
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
        f"SELECT DISTINCT {columna} FROM venues WHERE {columna} IS NOT NULL AND {columna} != '' ORDER BY {columna}"
    ).fetchall()
    conn.close()
    return [f[0] for f in filas]


if __name__ == "__main__":
    # Si corres  python3 database.py  directamente, crea la base.
    crear_base()
