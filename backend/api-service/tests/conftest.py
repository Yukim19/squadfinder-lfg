"""Configuración de las pruebas.

Usan una base de datos aparte, "<tu base>_test", en el mismo servidor de DATABASE_URL.
Antes de CADA prueba se recrea desde cero con schema.sql, seed.sql y seed_demo.sql,
así las pruebas no dependen unas de otras.
"""

import os
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

RAIZ_API = Path(__file__).resolve().parents[1]
CARPETA_SQL = RAIZ_API.parent / "database"


def _url_base() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    for linea in (RAIZ_API / ".env").read_text(encoding="utf-8").splitlines():
        if linea.strip().startswith("DATABASE_URL="):
            return linea.split("=", 1)[1].strip()
    raise RuntimeError("Falta DATABASE_URL en backend/api-service/.env")


URL_BASE = _url_base()
NOMBRE_TEST = f"{conninfo_to_dict(URL_BASE)['dbname']}_test"
URL_TEST = make_conninfo(URL_BASE, dbname=NOMBRE_TEST)
SCRIPTS = [(CARPETA_SQL / n).read_text(encoding="utf-8") for n in ("schema.sql", "seed.sql", "seed_demo.sql")]

# La app lee la configuración de estas variables
os.environ.update(DATABASE_URL=URL_TEST, ENVIRONMENT="test", AUTH_MODE="dev")


@pytest.fixture(scope="session", autouse=True)
def base_de_pruebas():
    with psycopg.connect(make_conninfo(URL_BASE, dbname="postgres"), autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(NOMBRE_TEST)))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(NOMBRE_TEST)))
    yield


@pytest.fixture(autouse=True)
def datos_limpios(base_de_pruebas):
    with psycopg.connect(URL_TEST, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for script in SCRIPTS:
            conn.execute(script)


@pytest.fixture(scope="session")
def cliente():
    from app.config import get_settings
    from app.main import crear_app

    get_settings.cache_clear()
    with TestClient(crear_app()) as c:
        yield c


@pytest.fixture
def db():
    """Conexión directa para preparar o comprobar datos en una prueba."""
    with psycopg.connect(URL_TEST, autocommit=True) as conn:
        yield conn


def como(usuario: str) -> dict:
    """Encabezado de autenticación en modo desarrollo: como("ana") -> usuario demo|ana."""
    return {"X-Dev-User": f"demo|{usuario}"}
