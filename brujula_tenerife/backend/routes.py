"""Herramienta ``recommend_route(zona, duracion_horas)``.

Traslado directo de las celdas 40 y 42 del notebook. La recomendación se
genera con el RAG para conservar las fuentes del documento.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from .rag import RagIndex

logger = logging.getLogger(__name__)

ROUTE_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "name": "recommend_route",
    "description": (
        "Recomienda una ruta turística por una zona de Tenerife "
        "teniendo en cuenta las horas disponibles."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "zona": {
                "type": "string",
                "description": (
                    "Zona de Tenerife que el usuario quiere visitar. "
                    "Por ejemplo: Anaga, Teide o Santa Cruz."
                ),
            },
            "duracion_horas": {
                "type": "integer",
                "description": "Número de horas disponibles para realizar la ruta.",
                "minimum": 1,
                "maximum": 12,
            },
        },
        "required": ["zona", "duracion_horas"],
        "additionalProperties": False,
    },
}

route_tool_logs: list[dict[str, Any]] = []


def recommend_route(rag: RagIndex, zona: str, duracion_horas: int) -> dict[str, Any]:
    """Recomienda una ruta turística utilizando el RAG."""
    start_time = time.perf_counter()

    if not isinstance(zona, str) or not zona.strip():
        result: dict[str, Any] = {"success": False, "error": "La zona no puede estar vacía."}
    elif isinstance(duracion_horas, bool) or not isinstance(duracion_horas, int):
        result = {"success": False, "error": "La duración debe ser un número entero."}
    elif not 1 <= duracion_horas <= 12:
        result = {"success": False, "error": "La duración debe estar entre 1 y 12 horas."}
    else:
        normalized_zone = zona.strip()
        question = (
            f"Recomienda una ruta turística por {normalized_zone} "
            f"para una duración aproximada de {duracion_horas} horas. "
            "Utiliza únicamente la información de la guía turística."
        )
        try:
            rag_result = rag.answer_with_rag(question)
            result = {
                "success": True,
                "zona": normalized_zone,
                "duracion_horas": duracion_horas,
                "recommendation": rag_result["answer"],
                "sources": rag_result["sources"],
            }
        except Exception as exc:  # noqa: BLE001 - se devuelve un error controlado
            result = {
                "success": False,
                "error": "No se ha podido generar la recomendación.",
                "error_type": type(exc).__name__,
            }

    log_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "zona": str(zona)[:60],
        "duracion_horas": duracion_horas,
        "success": result["success"],
        "elapsed_seconds": round(time.perf_counter() - start_time, 2),
    }
    route_tool_logs.append(log_entry)
    logger.info("recommend_route %s", log_entry)
    return result
