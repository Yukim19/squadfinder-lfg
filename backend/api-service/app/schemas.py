"""Modelos de entrada (validación con Pydantic). Reflejan los CHECK de schema.sql."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Tipos con las mismas reglas que la base de datos
Username = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_]{3,30}$")]
Region = Literal["NA_EAST", "NA_WEST", "LATAM_NORTH", "LATAM_SOUTH", "BRAZIL", "EUROPE", "ASIA", "OCEANIA"]
IdiomaUi = Literal["es", "en"]
IdiomaUsuario = Literal["es", "en", "both"]
NivelFiltro = Literal["OFF", "MEDIUM", "STRICT"]
Proveedor = Literal["discord", "steam", "twitch", "kick"]
TextoCorto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Plataforma = Literal["PC", "PlayStation", "Xbox", "Switch", "Mobile"]
ModoJuego = Literal["CASUAL", "COMPETITIVE"]
IdiomaSala = Literal["es", "en", "any"]
Titulo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=100)]
Descripcion = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Rango = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


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


# ---------------------------------------------------------------------------
# Salas (LFG) y solicitudes
# ---------------------------------------------------------------------------
class SalaCrear(Entrada):
    game_id: int
    title: Titulo
    description: Descripcion | None = None
    max_players: int = Field(ge=2, le=10)
    play_mode: ModoJuego = "CASUAL"
    rank_required: Rango | None = None
    mic_required: bool = False
    required_language: IdiomaSala = "es"
    platforms: list[Plataforma] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def _rango_solo_competitivo(self):
        if self.play_mode == "CASUAL" and self.rank_required:
            raise ValueError("Solo las salas competitivas pueden pedir un rango mínimo")
        return self


class SalaActualizar(Entrada):
    """Solo el anfitrión. El juego no se cambia: para otro juego se crea otra sala."""

    title: Titulo | None = None
    description: Descripcion | None = None
    max_players: int | None = Field(default=None, ge=2, le=10)
    play_mode: ModoJuego | None = None
    rank_required: Rango | None = None
    mic_required: bool | None = None
    required_language: IdiomaSala | None = None
    platforms: list[Plataforma] | None = Field(default=None, min_length=1, max_length=5)
    # OPEN <-> FULL lo maneja la API al aceptar o salir jugadores
    status: Literal["IN_PROGRESS", "CLOSED"] | None = None


class SolicitudCrear(Entrada):
    message: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None


class SolicitudDecision(Entrada):
    status: Literal["ACCEPTED", "REJECTED"]


# ---------------------------------------------------------------------------
# Reputación y reportes
# ---------------------------------------------------------------------------
Etiqueta = Literal["GREAT_LEADER", "FRIENDLY", "GOOD_COMMS", "SKILLED", "TEAM_PLAYER"]
Comentario = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


class ResenaCrear(Entrada):
    post_id: int
    target_user_id: int
    rating: int = Field(ge=1, le=5)
    tag: Etiqueta | None = None
    comment: Comentario | None = None


class ResenaActualizar(Entrada):
    rating: int | None = Field(default=None, ge=1, le=5)
    tag: Etiqueta | None = None
    comment: Comentario | None = None


class ReporteCrear(Entrada):
    reported_user_id: int
    post_id: int = Field(description="Partida donde ocurrió; el chat de esa sala sirve de evidencia")
    reason: Literal["TOXIC_CHAT", "HARASSMENT", "AFK_GRIEFING", "CHEATING", "OTHER"]
    comment: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=500)]


# ---------------------------------------------------------------------------
# Administración
# ---------------------------------------------------------------------------
class ResolverReporte(Entrada):
    """Si no se envían días o niveles se usan los valores de las reglas de moderación."""

    action: Literal["DISMISSED", "WARNED", "SUSPENDED", "BANNED"]
    suspension_days: int | None = Field(default=None, ge=1, le=365)
    levels_removed: int | None = Field(default=None, ge=0, le=10)
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class ReglasModeracion(Entrada):
    warnings_limit: int | None = Field(default=None, ge=1, le=10)
    auto_action: Literal["SUSPEND", "BAN"] | None = None
    auto_suspension_days: int | None = Field(default=None, ge=1, le=365)
    warning_levels_removed: int | None = Field(default=None, ge=0, le=10)
    suspension_levels_removed: int | None = Field(default=None, ge=0, le=10)


class DecisionJuego(Entrada):
    """Aprobar crea el juego en el catálogo; rechazar solo cierra la sugerencia."""

    status: Literal["APPROVED", "REJECTED"]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)] | None = Field(
        default=None, description="Nombre final del juego; si no se envía se usa el sugerido")
    genre_id: int | None = None
    platforms: list[Plataforma] | None = Field(default=None, min_length=1, max_length=5)
    crossplay: bool = False

    @model_validator(mode="after")
    def _datos_para_aprobar(self):
        if self.status == "APPROVED" and (self.genre_id is None or not self.platforms):
            raise ValueError("Para aprobar un juego hay que indicar el género y al menos una plataforma")
        return self
