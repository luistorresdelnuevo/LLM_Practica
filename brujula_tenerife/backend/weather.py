"""Herramienta ``get_weather(fecha)``.

El notebook todavía no implementa esta herramienta, así que se usa una
**simulación declarada**: el pronóstico es determinista a partir de la fecha
y la respuesta indica ``"simulated": True``. Sigue el mismo patrón que
``recommend_route``: validación, resultado serializable y registro sin datos
sensibles.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

MAX_FORECAST_DAYS = 14

WEATHER_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "name": "get_weather",
    "description": (
        "Devuelve el pronóstico meteorológico de Tenerife para una fecha. "
        "Úsala solo cuando el usuario pregunte por el tiempo o el clima."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "fecha": {
                "type": "string",
                "description": "Fecha en formato AAAA-MM-DD.",
            },
        },
        "required": ["fecha"],
        "additionalProperties": False,
    },
}

_CONDITIONS = [
    "soleado",
    "parcialmente nuboso",
    "nuboso con claros",
    "intervalos de lluvia débil",
    "calima ligera",
]

weather_tool_logs: list[dict[str, Any]] = []


def get_weather(fecha: str, *, today: date | None = None) -> dict[str, Any]:
    """Devuelve un pronóstico simulado y determinista para ``fecha``.

    Args:
        fecha: fecha en formato ``AAAA-MM-DD``.
        today: fecha de referencia; se inyecta en las pruebas.

    Returns:
        Diccionario con ``success`` y los datos o un ``error`` legible.
    """
    start_time = time.perf_counter()
    today = today or date.today()

    try:
        target = datetime.strptime(str(fecha).strip(), "%Y-%m-%d").date()
    except ValueError:
        result: dict[str, Any] = {
            "success": False,
            "error": "La fecha debe tener el formato AAAA-MM-DD.",
        }
    else:
        if target < today:
            result = {"success": False, "error": "No hay pronóstico para fechas pasadas."}
        elif target > today + timedelta(days=MAX_FORECAST_DAYS):
            result = {
                "success": False,
                "error": f"Solo hay pronóstico para los próximos {MAX_FORECAST_DAYS} días.",
            }
        else:
            seed = int(hashlib.sha256(target.isoformat().encode()).hexdigest(), 16)
            result = {
                "success": True,
                "simulated": True,
                "fecha": target.isoformat(),
                "lugar": "Tenerife",
                "condicion": _CONDITIONS[seed % len(_CONDITIONS)],
                "temperatura_min_c": 16 + seed % 4,
                "temperatura_max_c": 22 + (seed // 7) % 6,
                "probabilidad_lluvia": (seed // 11) % 60,
            }

    log_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "fecha": str(fecha)[:20],
        "success": result["success"],
        "elapsed_seconds": round(time.perf_counter() - start_time, 4),
    }
    weather_tool_logs.append(log_entry)
    logger.info("get_weather %s", log_entry)
    return result
