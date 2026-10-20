"""Orquestación del asistente: enrutado, herramientas, RAG y memoria.

Flujo de cada mensaje:

1. Se envía al modelo el historial reciente y la pregunta con las dos
   herramientas disponibles (patrón ``run_llm_with_tools`` de la sesión 04).
2. Si el modelo pide ``get_weather`` o ``recommend_route``, Python ejecuta la
   herramienta, devuelve su salida y el modelo redacta la respuesta final.
3. Si no pide herramientas, la pregunta se responde con
   ``answer_with_rag`` sobre la pregunta contextualizada con el historial,
   exactamente como ``answer_with_memory`` en el notebook.
4. Las citas salen de los metadatos de los chunks recuperados, nunca del texto
   del modelo.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from .config import INSUFFICIENT_INFO, Settings
from .conversation import ConversationStore, contextualize_question
from .personas import build_style
from .game_adapter import ChatRequest, ChatResponse, Citation, session_id_for
from .rag import RagIndex
from .routes import ROUTE_TOOL_SCHEMA, recommend_route
from .weather import WEATHER_TOOL_SCHEMA, get_weather

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3

FRIENDLY_ERROR = (
    "Ahora mismo no puedo consultar mis notas de viaje. "
    "Inténtalo de nuevo en unos segundos."
)

ROUTER_INSTRUCTIONS = """
Eres el guía turístico de Tenerife dentro de un videojuego.
Hoy es {today}. El jugador está en la zona: {scene}.

Decide si necesitas una herramienta:
- Si pregunta por el tiempo, el clima o la lluvia, llama a get_weather con la
  fecha en formato AAAA-MM-DD (convierte "hoy", "mañana", etc.).
- Llama a recommend_route SOLO si el jugador pide explícitamente una "ruta",
  un "itinerario" o un plan para un número de horas concreto. Si no indica la
  zona usa la zona actual del jugador; si no indica la duración usa 4 horas.
- Preguntas como "¿qué visitar?", "¿qué ver?" o "¿qué playa hay?" NO son
  peticiones de ruta: no llames a ninguna herramienta.
- En cualquier otro caso NO llames a ninguna herramienta y responde solo: RAG

Cuando recibas el resultado de una herramienta, redacta una respuesta breve
en español basada únicamente en ese resultado. Si la herramienta indica que el
pronóstico es simulado, menciónalo. Si el resultado contiene referencias
[Fuente N], conserva cada una junto a la afirmación que respalda. Si la
herramienta devuelve un error, explícalo.
""".strip()


class WeatherArgs(BaseModel):
    """Argumentos validados de ``get_weather``."""

    fecha: str = Field(min_length=1, max_length=20)


class RouteArgs(BaseModel):
    """Argumentos validados de ``recommend_route``."""

    zona: str = Field(min_length=1, max_length=60)
    duracion_horas: int = Field(ge=1, le=12)


_REFERENCE_RE = re.compile(r"Fuente\s+(\d+)")


def select_citations(answer: str, sources: list[dict[str, Any]]) -> list[Citation]:
    """Devuelve las fuentes citadas en la respuesta, con metadatos reales.

    Si la respuesta reconoce falta de información no se devuelven citas. Si el
    modelo no marcó referencias, se devuelven todas las fuentes recuperadas.
    """
    if INSUFFICIENT_INFO.lower() in answer.lower():
        return []
    cited = {f"Fuente {n}" for n in _REFERENCE_RE.findall(answer)}
    chosen = [s for s in sources if s["reference"] in cited] or sources
    return [
        Citation(
            reference=s["reference"],
            source=str(s["source"]),
            page=str(s["page"]),
            chunk_id=str(s["chunk_id"]),
            score=round(float(s["score"]), 4),
        )
        for s in chosen
    ]


class TourismAssistant:
    """Asistente turístico con RAG, memoria por jugador y herramientas."""

    def __init__(
        self,
        client: Any,
        settings: Settings,
        rag: RagIndex,
        store: ConversationStore | None = None,
        today_provider: Callable[[], date] = date.today,
    ) -> None:
        self.client = client
        self.settings = settings
        self.rag = rag
        self.store = store or ConversationStore()
        self.today_provider = today_provider

    # ------------------------------------------------------------------
    def chat(self, request: ChatRequest) -> ChatResponse:
        """Procesa un mensaje del juego y devuelve el contrato estable."""
        session_id = session_id_for(request.player_id)
        history = self.store.recent(session_id)
        try:
            answer, sources, tools_used = self._answer(request, history)
        except Exception as exc:  # noqa: BLE001 - nunca se propaga al juego
            logger.warning("Fallo del asistente (%s)", type(exc).__name__)
            return ChatResponse(
                answer=FRIENDLY_ERROR,
                session_id=session_id,
                error=f"El asistente no pudo responder ({type(exc).__name__}).",
            )

        self.store.append(session_id, request.message, answer)
        return ChatResponse(
            answer=answer,
            citations=select_citations(answer, sources),
            tools_used=tools_used,
            session_id=session_id,
        )

    # ------------------------------------------------------------------
    def _answer(
        self, request: ChatRequest, history: list[dict[str, str]]
    ) -> tuple[str, list[dict[str, Any]], list[str]]:
        """Devuelve respuesta, fuentes y nombres de herramientas usadas."""
        context = request.game_context
        style = build_style(context.persona, context.npc)
        instructions = ROUTER_INSTRUCTIONS.format(
            today=self.today_provider().isoformat(),
            scene=context.scene,
        )
        if style:
            instructions = f"{instructions}\n\n{style}"
        conversation: list[Any] = []
        for turn in history:
            conversation.append({"role": "user", "content": turn["question"]})
            conversation.append({"role": "assistant", "content": turn["answer"]})
        conversation.append({"role": "user", "content": request.message})

        sources: list[dict[str, Any]] = []
        tools_used: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.responses.create(
                model=self.settings.generation_model,
                instructions=instructions,
                input=conversation,
                tools=[WEATHER_TOOL_SCHEMA, ROUTE_TOOL_SCHEMA],
                tool_choice="auto",
                temperature=self.settings.temperature,
                max_output_tokens=self.settings.max_output_tokens,
            )
            calls = [item for item in response.output if item.type == "function_call"]

            if not calls:
                if not tools_used:
                    # Pregunta turística o de seguimiento: RAG + historial.
                    rag_result = self.rag.answer_with_rag(
                        contextualize_question(request.message, history), style=style
                    )
                    return rag_result["answer"], rag_result["sources"], []
                return response.output_text, sources, tools_used

            conversation.extend(response.output)
            for call in calls:
                payload = self._run_tool(call.name, call.arguments)
                if call.name not in tools_used:
                    tools_used.append(call.name)
                sources.extend(payload.get("sources", []))
                conversation.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(payload, ensure_ascii=False),
                    }
                )

        raise RuntimeError("Se alcanzó el límite de rondas de herramientas.")

    def _run_tool(self, name: str, raw_arguments: str) -> dict[str, Any]:
        """Valida los argumentos con Pydantic y ejecuta la herramienta."""
        try:
            arguments = json.loads(raw_arguments or "{}")
            if name == "get_weather":
                args = WeatherArgs.model_validate(arguments)
                return get_weather(args.fecha, today=self.today_provider())
            if name == "recommend_route":
                route = RouteArgs.model_validate(arguments)
                return recommend_route(self.rag, route.zona, route.duracion_horas)
            return {"success": False, "error": f"Herramienta no registrada: {name}"}
        except (json.JSONDecodeError, ValidationError) as exc:
            return {
                "success": False,
                "error": "Argumentos inválidos para la herramienta.",
                "error_type": type(exc).__name__,
            }
