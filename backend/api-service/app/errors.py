"""Errores de la API con un formato JSON uniforme:

    {"error": {"code": "USERNAME_TAKEN", "message": "Ese nombre de usuario ya existe.", "details": null}}

`code` es estable (lo usa el frontend); `message` es para mostrar al usuario.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg

log = logging.getLogger("api")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: object = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def respuesta_error(status: int, code: str, message: str, details: object = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return respuesta_error(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        campos = [
            {"campo": ".".join(str(p) for p in e["loc"] if p != "body"), "problema": e["msg"]}
            for e in exc.errors()
        ]
        return respuesta_error(422, "VALIDATION_ERROR", "Hay datos inválidos en la petición.", campos)

    # Las restricciones de la base de datos son la última línea de defensa
    @app.exception_handler(pg.UniqueViolation)
    async def _unico(_: Request, exc: pg.UniqueViolation) -> JSONResponse:
        return respuesta_error(409, "ALREADY_EXISTS", "Ese registro ya existe.", exc.diag.constraint_name)

    @app.exception_handler(pg.ForeignKeyViolation)
    async def _llave_foranea(_: Request, exc: pg.ForeignKeyViolation) -> JSONResponse:
        return respuesta_error(422, "INVALID_REFERENCE", "Uno de los datos hace referencia a algo que no existe.",
                               exc.diag.constraint_name)

    @app.exception_handler(pg.CheckViolation)
    async def _check(_: Request, exc: pg.CheckViolation) -> JSONResponse:
        return respuesta_error(422, "INVALID_VALUE", "Un valor no cumple las reglas de la base de datos.",
                               exc.diag.constraint_name)

    # RAISE EXCEPTION de los triggers y funciones (por ejemplo, crossplay)
    @app.exception_handler(pg.RaiseException)
    async def _regla_negocio(_: Request, exc: pg.RaiseException) -> JSONResponse:
        return respuesta_error(422, "BUSINESS_RULE", exc.diag.message_primary or "Operación no permitida.")

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Error no controlado", exc_info=exc)
        return respuesta_error(500, "INTERNAL_ERROR", "Ocurrió un error inesperado. Inténtalo de nuevo.")
