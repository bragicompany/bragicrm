"""
db_tools.py — Exportar / importar la base a un archivo PORTÁTIL (JSON).  (Fase 6C-1)

¿Para qué? Dos cosas:
  1) Un respaldo EXTRA, legible y a prueba de futuro (no depende de SQLite).
  2) El vehículo para mover tus datos a Postgres en la nube (6C-3) SIN perder nada:
     se exporta de aquí y se importa allá.

REGLA DE ORO: exportar es 100% de solo lectura (no toca tu base). Importar SOLO
inserta en una base cuyas tablas estén vacías (no pisa datos existentes).

USO (en la terminal):
  python3 db_tools.py export                 # crea backups/export_<fecha>.json
  python3 db_tools.py export mi_copia.json   # a un archivo concreto
  python3 db_tools.py import export.json     # importa a la base actual (si está vacía)
"""

import os
import sys
import json
from datetime import datetime

import database

# Tablas que se exportan/importan, en orden seguro (venues primero por las llaves foráneas).
TABLAS = ["venues", "actividades", "mensajes"]


def exportar(ruta=None):
    """Vuelca todas las tablas a un JSON portátil. Solo lectura: no modifica la base."""
    conn = database.conectar()
    datos = {
        "_meta": {
            "exportado_el": datetime.now().isoformat(timespec="seconds"),
            "origen": database.DB_FILE,
            "tablas": TABLAS,
        }
    }
    total = 0
    for tabla in TABLAS:
        filas = conn.execute(f"SELECT * FROM {tabla}").fetchall()
        datos[tabla] = [dict(f) for f in filas]
        total += len(filas)
    conn.close()

    if not ruta:
        os.makedirs(database.BACKUP_DIR, exist_ok=True)
        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta = os.path.join(database.BACKUP_DIR, f"export_{sello}.json")

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    resumen = ", ".join(f"{t}: {len(datos[t])}" for t in TABLAS)
    print(f"Exportadas {total} filas ({resumen}) -> {ruta}")
    return ruta


def _tabla_vacia(conn, tabla):
    return conn.execute(f"SELECT COUNT(*) AS n FROM {tabla}").fetchone()["n"] == 0


def importar(ruta):
    """Carga un JSON exportado en la base ACTUAL. Por seguridad, solo importa en
    tablas que estén vacías (evita duplicar o pisar datos reales)."""
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    database.crear_base()
    database.migrar()
    conn = database.conectar()

    # Guarda de seguridad: si alguna tabla con datos ya tiene filas, no importamos.
    no_vacias = [t for t in TABLAS if datos.get(t) and not _tabla_vacia(conn, t)]
    if no_vacias:
        conn.close()
        raise SystemExit(
            "ABORTADO: estas tablas ya tienen datos -> " + ", ".join(no_vacias) +
            ". Importa solo en una base vacía (para la migración a la nube)."
        )

    total = 0
    columnas_por_tabla = {t: database._columnas_existentes(t) for t in TABLAS}
    for tabla in TABLAS:
        for fila in datos.get(tabla, []):
            # Solo columnas que existan en la base destino (tolera diferencias de versión).
            fila = {k: v for k, v in fila.items() if k in columnas_por_tabla[tabla]}
            if not fila:
                continue
            cols = ", ".join(fila.keys())
            marc = ", ".join(["?"] * len(fila))
            conn.execute(f"INSERT INTO {tabla} ({cols}) VALUES ({marc})", list(fila.values()))
            total += 1
    conn.commit()

    # En Postgres, al importar con ids explícitos hay que adelantar la secuencia del
    # id; si no, el próximo INSERT chocaría con un id repetido.
    if database.es_postgres():
        for tabla in TABLAS:
            conn.execute(
                f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {tabla}), 1))"
            )
        conn.commit()

    conn.close()
    print(f"Importadas {total} filas desde {ruta}.")
    return total


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("export", "import"):
        print(__doc__)
        return
    accion = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if accion == "export":
        exportar(arg)
    else:
        if not arg:
            print("Falta el archivo a importar:  python3 db_tools.py import export.json")
            return
        importar(arg)


if __name__ == "__main__":
    main()
