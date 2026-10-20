"""Contrato HTTP entre el asistente y el videojuego.

El juego solo conoce estos modelos Pydantic; nunca objetos del RAG.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PLAYER_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class GameContext(BaseModel):
    """Estado mínimo del juego que puede llegar al LLM."""

    model_config = ConfigDict(extra="forbid")

    scene: str = Field(default="desconocida", max_length=40)
    quest: str | None = Field(default=None, max_length=80)
    npc: str | None = Field(default=None, max_length=40)
    persona: Literal["guia", "noir"] = "guia"


class ChatRequest(BaseModel):
    """Petición de ``POST /chat``."""

    model_config = ConfigDict(extra="forbid")

    player_id: str = Field(pattern=PLAYER_ID_PATTERN)
    message: str = Field(min_length=1, max_length=500)
    game_context: GameContext = Field(default_factory=GameContext)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        """Rechaza mensajes formados solo por espacios."""
        value = value.strip()
        if not value:
            raise ValueError("El mensaje no puede estar vacío.")
        return value


class Citation(BaseModel):
    """Fuente construida desde los metadatos reales del chunk."""

    reference: str
    source: str
    page: str
    chunk_id: str
    score: float


class ChatResponse(BaseModel):
    """Respuesta estable de ``POST /chat``."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    session_id: str
    error: str | None = None


def session_id_for(player_id: str) -> str:
    """Traduce un ``player_id`` a su identificador de conversación."""
    return f"partida-{player_id}"
