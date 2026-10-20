"""Configuración del backend, cargada desde el ``.env`` del proyecto.

Replica las lecturas y comprobaciones de la celda de configuración del
notebook. La clave nunca se incluye en ``repr`` ni en los logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
BRUJULA_DIR = PACKAGE_DIR.parent
PROJECT_DIR = BRUJULA_DIR.parent
ENV_PATH = PROJECT_DIR / ".env"
PDF_PATH = PROJECT_DIR / "data" / "TENERIFE.pdf"
CACHE_DIR = BRUJULA_DIR / "cache"
LOGS_DIR = BRUJULA_DIR / "logs"

# Configuración de chunking seleccionada en el notebook (experimento "B").
SELECTED_EXPERIMENT = "B"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200

# Número máximo de turnos anteriores enviados al modelo (notebook, sección 6).
MAX_HISTORY_TURNS = 5

INSUFFICIENT_INFO = "No tengo información suficiente en la base documental"


@dataclass(frozen=True)
class Settings:
    """Parámetros validados del asistente."""

    generation_model: str
    embedding_model: str
    temperature: float
    top_p: float
    max_output_tokens: int
    top_k: int
    api_host: str
    api_port: int
    openai_api_key: str = field(repr=False)

    @property
    def has_api_key(self) -> bool:
        """Indica si hay clave sin revelar su valor."""
        return bool(self.openai_api_key)


def load_settings(env_path: Path = ENV_PATH) -> Settings:
    """Carga y valida la configuración igual que el notebook.

    Raises:
        ValueError: si el proveedor no es OpenAI o un parámetro no es válido.
    """
    load_dotenv(env_path)

    provider = os.environ.get("LLM_PROVIDER", "openai")
    if provider != "openai":
        raise ValueError(f"Proveedor no soportado: {provider}")

    settings = Settings(
        generation_model=os.environ.get("OPENAI_CHAT_MODEL", ""),
        embedding_model=os.environ.get("OPENAI_EMBEDDING_MODEL", ""),
        temperature=float(os.environ.get("LLM_TEMPERATURE", "0.2")),
        top_p=float(os.environ.get("LLM_TOP_P", "1.0")),
        max_output_tokens=int(os.environ.get("LLM_MAX_OUTPUT_TOKENS", "250")),
        top_k=int(os.environ.get("RAG_TOP_K", "3")),
        api_host=os.environ.get("ASSISTANT_API_HOST", "127.0.0.1"),
        api_port=int(os.environ.get("ASSISTANT_API_PORT", "8077")),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    )

    if not settings.generation_model or not settings.embedding_model:
        raise ValueError("Faltan OPENAI_CHAT_MODEL u OPENAI_EMBEDDING_MODEL.")
    if settings.top_k <= 0:
        raise ValueError("RAG_TOP_K debe ser mayor que cero.")
    return settings
