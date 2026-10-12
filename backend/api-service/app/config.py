"""Configuración leída de variables de entorno (o del archivo .env)."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str

    # "auth0": valida el JWT de Auth0. "dev": el usuario llega en el encabezado X-Dev-User.
    auth_mode: Literal["auth0", "dev"] = "auth0"
    auth0_domain: str | None = None
    auth0_audience: str | None = None

    cors_origins: list[str] = ["http://127.0.0.1:5500", "http://localhost:5500"]

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
