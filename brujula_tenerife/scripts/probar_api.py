"""Prueba manual de extremo a extremo contra la API local en ejecución.

Uso (con la API iniciada)::

    python scripts/probar_api.py

Hace llamadas reales al modelo: consume una pequeña cantidad de tokens.
"""

from __future__ import annotations

import json
import sys

import requests

API_URL = "http://127.0.0.1:8077/chat"

CASES = [
    ("demo_a", "Anaga", "¿Qué se recomienda visitar en el Parque Rural de Anaga?"),
    ("demo_a", "Anaga", "¿Y qué playa se recomienda allí?"),
    ("demo_b", "Anaga", "¿Y qué playa se recomienda allí?"),
    ("demo_c", "Teide", "¿Qué tiempo hará mañana?"),
    ("demo_c", "Santa Cruz", "Recomiéndame una ruta de 3 horas por Santa Cruz"),
    ("demo_d", "Teide", "¿Cuál es la capital de Japón?"),
]


def main() -> int:
    """Ejecuta los casos y muestra respuesta, herramientas y citas."""
    for player_id, scene, message in CASES:
        body = {"player_id": player_id, "message": message,
                "game_context": {"scene": scene, "quest": "Sellos de la brújula"}}
        try:
            data = requests.post(API_URL, json=body, timeout=60).json()
        except requests.RequestException as exc:
            print("La API no responde:", type(exc).__name__)
            return 1
        print("=" * 78)
        print(f"[{player_id} @ {scene}] {message}")
        print("Respuesta:", data["answer"])
        print("Herramientas:", data["tools_used"], "| Error:", data["error"])
        print("Citas:", json.dumps([(c["reference"], c["page"], c["chunk_id"])
                                    for c in data["citations"]], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
