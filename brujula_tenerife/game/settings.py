"""Constantes del videojuego. No contiene claves ni lógica del LLM."""

from __future__ import annotations

import os
import uuid

TITLE = "Tenerife Noir · El caso del Faro"
TILE = 32
MAP_COLS = 30
MAP_ROWS = 20
WIDTH = TILE * MAP_COLS
HEIGHT = TILE * MAP_ROWS
FPS = 60

PLAYER_SPEED = 180  # píxeles por segundo
PLAYER_SIZE = 22
INTERACT_DISTANCE = 56

API_URL = os.environ.get("BRUJULA_API_URL", "http://127.0.0.1:8077/chat")
API_TIMEOUT_SECONDS = 60.0
QUEST_NAME = "El caso del Faro"
# Tono de las respuestas: "noir" (informantes) o "guia" (neutro del notebook).
PERSONA = os.environ.get("BRUJULA_PERSONA", "noir")

# Identificador estable durante toda la partida.
PLAYER_ID = f"jugador-{uuid.uuid4().hex[:10]}"

# Paleta original basada en formas simples.
COLORS: dict[str, tuple[int, int, int]] = {
    "sea": (38, 104, 160),
    "sea_light": (58, 128, 186),
    "sand": (226, 204, 150),
    "grass": (104, 160, 84),
    "forest": (40, 110, 64),
    "tree": (24, 78, 44),
    "lava": (120, 90, 74),
    "rock": (86, 74, 70),
    "snow": (236, 236, 240),
    "road": (176, 170, 160),
    "building": (204, 120, 90),
    "roof": (150, 70, 60),
    "player": (250, 214, 64),
    "player_outline": (60, 40, 20),
    "text": (245, 245, 245),
    "text_dim": (190, 196, 210),
    "panel": (20, 26, 40),
    "panel_border": (230, 200, 120),
    "accent": (255, 220, 120),
    "error": (255, 130, 120),
    "ok": (150, 230, 160),
    "hint": (255, 255, 255),
}
