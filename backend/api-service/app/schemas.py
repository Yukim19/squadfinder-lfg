"""Modelos de entrada (validación con Pydantic). Reflejan los CHECK de schema.sql."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Tipos con las mismas reglas que la base de datos
Username = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]{3,30}$")]
Region = Literal["NA_EAST", "NA_WEST", "LATAM_NORTH", "LATAM_SOUTH", "BRAZIL", "EUROPE", "ASIA", "OCEANIA"]
IdiomaUi = Literal["es", "en"]
IdiomaUsuario = Literal["es", "en", "both"]
NivelFiltro = Literal["OFF", "MEDIUM", "STRICT"]
Proveedor = Literal["discord", "steam", "twitch", "kick"]
TextoCorto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class Entrada(BaseModel):
    # Rechaza campos que no existen (evita errores de escritura silenciosos en el frontend)
    model_config = ConfigDict(extra="forbid")


class Onboarding(Entrada):
    username: Username
    region: Region
    preferred_language_speak: IdiomaUsuario = "es"
    preferred_language_write: IdiomaUsuario = "es"
    toxicity_filter_level: NivelFiltro = "MEDIUM"
    ui_language: IdiomaUi = "es"
    games: list[int] = Field(min_length=1, max_length=50, description="Juegos en los que busca compañeros")
    genres: list[int] = Field(default_factory=list, max_length=20)


class PerfilActualizar(Entrada):
    """Todos los campos son opcionales: solo se cambia lo que se envía."""

    username: Username | None = None
    region: Region | None = None
    preferred_language_speak: IdiomaUsuario | None = None
    preferred_language_write: IdiomaUsuario | None = None
    toxicity_filter_level: NivelFiltro | None = None
    ui_language: IdiomaUi | None = None
    avatar_url: Annotated[str, StringConstraints(max_length=500)] | None = None
    games: list[int] | None = Field(default=None, min_length=1, max_length=50)
    genres: list[int] | None = Field(default=None, max_length=20)


class CuentaVinculada(Entrada):
    external_username: TextoCorto
    external_id: Annotated[str, StringConstraints(max_length=64)] | None = None


class Bloqueo(Entrada):
    user_id: int
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None


class SugerenciaJuego(Entrada):
    game_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
    platforms_note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None = None
