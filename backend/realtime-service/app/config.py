"""Configuración leída de variables de entorno (o de los archivos .env)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CARPETA = Path(__file__).resolve().parents[1]

# En desarrollo se reutiliza el .env del api-service (misma base de datos) y, si existe,
# el .env propio de este servicio tiene prioridad. En producción todo viene de variables de entorno.
ARCHIVOS_ENV = (CARPETA.parent / "api-service" / ".env", CARPETA / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ARCHIVOS_ENV, env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str

    # "auth0": valida el JWT de Auth0. "dev": el token es el usuario de prueba (demo|ana).
    auth_mode: Literal["auth0", "dev"] = "auth0"
    auth0_domain: str | None = None
    auth0_audience: str | None = None

    cors_origins: list[str] = ["http://127.0.0.1:5500", "http://localhost:5500"]

    # Anti-spam: máximo de mensajes por persona en la ventana de segundos
    max_mensajes: int = 5
    ventana_segundos: float = 5.0

    @model_validator(mode="after")
    def validar_seguridad(self) -> "Settings":
        if self.environment == "production" and self.auth_mode != "auth0":
            raise ValueError("En producción AUTH_MODE debe ser 'auth0'")
        if self.auth_mode == "auth0" and not (self.auth0_domain and self.auth0_audience):
            raise ValueError("Con AUTH_MODE=auth0 hay que definir AUTH0_DOMAIN y AUTH0_AUDIENCE")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
