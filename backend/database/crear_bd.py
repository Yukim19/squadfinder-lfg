"""Crea (o recrea) la base de datos de SquadFinder ejecutando los scripts SQL.

Uso (desde la carpeta del proyecto):
    python backend/database/crear_bd.py                # schema + catálogo
    python backend/database/crear_bd.py --demo         # + datos de prueba
    python backend/database/crear_bd.py --reset --demo # borra todo y vuelve a crear

La conexión se toma de DATABASE_URL (variable de entorno o backend/api-service/.env).
Si la base de datos indicada no existe en el servidor, se crea.
Por seguridad, --reset solo funciona contra localhost salvo que se agregue --forzar.
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

CARPETA = Path(__file__).resolve().parent
ENV_API = CARPETA.parent / "api-service" / ".env"


def leer_database_url() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if ENV_API.exists():
        for linea in ENV_API.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("DATABASE_URL="):
                return linea.split("=", 1)[1].strip()
    sys.exit(f"No encontré DATABASE_URL (ni como variable de entorno ni en {ENV_API}).")


def asegurar_base(url: str) -> None:
    """Crea la base de datos si no existe, conectándose a la base 'postgres' del mismo servidor."""
    datos = conninfo_to_dict(url)
    nombre = datos.get("dbname")
    with psycopg.connect(make_conninfo(url, dbname="postgres"), autocommit=True) as conn:
        existe = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nombre,)).fetchone()
        if not existe:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
            print(f"Base de datos '{nombre}' creada.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo", action="store_true", help="cargar también seed_demo.sql")
    parser.add_argument("--reset", action="store_true", help="borrar todas las tablas antes de crearlas")
    parser.add_argument("--forzar", action="store_true", help="permitir --reset contra un servidor remoto")
    args = parser.parse_args()

    url = leer_database_url()
    host = conninfo_to_dict(url).get("host", "")
    if args.reset and host not in ("localhost", "127.0.0.1", "::1") and not args.forzar:
        sys.exit(f"--reset borraría todos los datos de '{host}'. Si de verdad quieres hacerlo, agrega --forzar.")

    if host in ("localhost", "127.0.0.1", "::1"):
        asegurar_base(url)

    scripts = ["schema.sql", "seed.sql"] + (["seed_demo.sql"] if args.demo else [])
    with psycopg.connect(url, autocommit=True) as conn:
        if args.reset:
            conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
            print("Esquema borrado.")
        for nombre in scripts:
            with conn.transaction():
                conn.execute((CARPETA / nombre).read_text(encoding="utf-8"))
            print(f"OK {nombre}")

        resumen = conn.execute(
            "SELECT (SELECT COUNT(*) FROM games) AS juegos, (SELECT COUNT(*) FROM users) AS usuarios, "
            "(SELECT COUNT(*) FROM lfg_posts) AS salas"
        ).fetchone()
        print(f"Listo: {resumen[0]} juegos, {resumen[1]} usuarios, {resumen[2]} salas.")


if __name__ == "__main__":
    main()
