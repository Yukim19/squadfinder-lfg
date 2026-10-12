"""Conexión a PostgreSQL con un pool de conexiones (psycopg 3)."""

from collections.abc import Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def abrir_pool(database_url: str) -> None:
    global _pool
    _pool = ConnectionPool(
        database_url,
        min_size=1,
        max_size=5,
        # autocommit: cada sentencia se guarda al instante. Las operaciones de varios
        # pasos usan `with db.transaction():` para que se guarden todas o ninguna.
        # prepare_threshold=None: sin sentencias preparadas, que el pooler de Neon (PgBouncer) no soporta.
        kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": None},
        # Neon cierra las conexiones inactivas: se revisan antes de usarlas
        check=ConnectionPool.check_connection,
        open=True,
    )


def cerrar_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_db() -> Iterator[Connection]:
    """Dependencia de FastAPI: una conexión del pool por petición."""
    if _pool is None:
        raise RuntimeError("El pool de conexiones no está abierto")
    with _pool.connection() as conn:
        yield conn


def conexion():
    """Conexión del pool para usar fuera de las dependencias de FastAPI (por ejemplo, en el WebSocket).

    Uso: `with conexion() as db: ...`
    """
    if _pool is None:
        raise RuntimeError("El pool de conexiones no está abierto")
    return _pool.connection()
