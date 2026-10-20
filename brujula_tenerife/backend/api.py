"""API local consumida por el videojuego.

Arranque (desde ``brujula_tenerife``)::

    python -m uvicorn backend.api:app --host 127.0.0.1 --port 8077

La clave se lee del ``.env`` del proyecto y nunca sale de este proceso.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import LOGS_DIR
from .game_adapter import ChatRequest, ChatResponse

logger = logging.getLogger("brujula.api")


def _configure_logging() -> None:
    """Registra en consola y en ``brujula_tenerife/logs/api.log``."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(getattr(h, "_brujula", False) for h in root.handlers):
        return
    handler = logging.FileHandler(LOGS_DIR / "api.log", encoding="utf-8")
    handler._brujula = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # Las librerías HTTP no deben volcar cabeceras ni cuerpos.
    for noisy in ("httpx", "openai", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def build_assistant():  # noqa: ANN201 - devuelve TourismAssistant
    """Crea el cliente OpenAI, el índice RAG y el asistente."""
    from openai import OpenAI

    from .assistant import TourismAssistant
    from .config import load_settings
    from .rag import RagIndex

    settings = load_settings()
    if not settings.has_api_key:
        raise ValueError("OPENAI_API_KEY no está configurada en el .env del backend.")
    client = OpenAI(api_key=settings.openai_api_key, timeout=30.0, max_retries=1)
    rag = RagIndex.build(client, settings)
    return TourismAssistant(client, settings, rag)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicializa el asistente una sola vez al arrancar."""
    _configure_logging()
    if getattr(app.state, "assistant", None) is None:
        try:
            app.state.assistant = build_assistant()
            app.state.startup_error = None
            logger.info("Asistente preparado")
        except Exception as exc:  # noqa: BLE001
            app.state.assistant = None
            app.state.startup_error = type(exc).__name__
            logger.error("No se pudo iniciar el asistente: %s", type(exc).__name__)
    yield


app = FastAPI(title="La brújula de Tenerife", version="1.0.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Devuelve errores de validación con el mismo contrato de respuesta."""
    fields = ", ".join(".".join(str(p) for p in e["loc"][1:]) for e in exc.errors())
    body = ChatResponse(
        answer="No he entendido la petición del juego.",
        session_id="",
        error=f"Petición inválida: {fields or 'cuerpo'}",
    )
    return JSONResponse(status_code=422, content=body.model_dump())


@app.get("/health")
def health() -> dict[str, object]:
    """Indica si el asistente está listo, sin revelar configuración."""
    ready = getattr(app.state, "assistant", None) is not None
    return {"status": "ok" if ready else "degraded", "assistant_ready": ready}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Responde a un mensaje del jugador mediante el asistente."""
    assistant = getattr(app.state, "assistant", None)
    if assistant is None:
        return ChatResponse(
            answer="El guía no está disponible: el backend no se ha iniciado bien.",
            session_id="",
            error="Asistente no inicializado. Revisa el .env y el log de la API.",
        )

    start = time.perf_counter()
    response = assistant.chat(request)
    logger.info(
        "chat player=%s scene=%s chars=%d tools=%s citations=%d error=%s seconds=%.2f",
        request.player_id,
        request.game_context.scene,
        len(request.message),
        response.tools_used,
        len(response.citations),
        bool(response.error),
        time.perf_counter() - start,
    )
    return response
