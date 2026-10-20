"""Pruebas del videojuego en modo sin ventana (SDL dummy)."""

from __future__ import annotations

import ast
import os
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from game.api_client import ApiClient  # noqa: E402
from game.dialogue import DialogueState  # noqa: E402
from game.main import Game  # noqa: E402
from game.settings import TILE  # noqa: E402

GAME_DIR = Path(__file__).resolve().parents[1] / "game"


def fake_poster(delay: float = 0.0, error: str | None = None) -> Any:
    """Simula ``requests.post`` con la estructura del contrato."""
    def post(url: str, json: dict, timeout: float) -> Any:
        time.sleep(delay)
        data = {"answer": f"Respuesta a {json['message']}", "tools_used": [],
                "citations": [{"source": "TENERIFE.pdf", "page": "5", "chunk_id": "B-5"}],
                "session_id": "partida-" + json["player_id"], "error": error}
        post.payloads.append(json)
        return SimpleNamespace(json=lambda: data)
    post.payloads = []
    return post


@pytest.fixture
def game() -> Any:
    poster = fake_poster(delay=0.2)
    g = Game(api=ApiClient(poster=poster), player_id="jugador-test", skip_intro=True)
    g.poster = poster
    yield g
    pygame.quit()


def press(key: int, text: str | None = None) -> None:
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=text or ""))
    if text:
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=text))


def type_text(text: str) -> None:
    for char in text:
        pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=char))


def wait_for_result(g: Any, seconds: float = 3.0) -> None:
    end = time.time() + seconds
    while g.api.pending and time.time() < end:
        g.step(1 / 60)
        time.sleep(0.01)


def teleport(g: Any, npc_index: int) -> None:
    g.player.pos.update(g.npcs[npc_index].rect.center)
    g.player.pos.x -= TILE
    g.player.rect.center = (round(g.player.pos.x), round(g.player.pos.y))


def test_player_moves(game: Any) -> None:
    start = game.player.pos.copy()
    game.player.move(pygame.Vector2(1, 0), 0.5, game.world)
    assert game.player.pos.x > start.x


def test_collision_blocks_sea(game: Any) -> None:
    for _ in range(200):
        game.player.move(pygame.Vector2(-1, 0), 1 / 60, game.world)
    assert not game.world.is_solid_at(game.player.rect.left, game.player.rect.centery)
    assert game.player.rect.left > 2 * TILE, "el mar del oeste detiene al jugador"


def test_npcs_are_on_walkable_tiles(game: Any) -> None:
    for npc in game.npcs:
        assert not game.world.is_solid_at(*npc.rect.center)
        assert game.world.zone_at(npc.rect.center) == npc.zone


def test_dialogue_open_type_send_and_close(game: Any) -> None:
    teleport(game, 0)
    assert game.nearby_npc() is game.npcs[0]
    press(pygame.K_e, "e")
    game.step(1 / 60)
    assert game.dialogue.is_open and game.dialogue.input_text == ""

    type_text("¿Qué ver?")
    press(pygame.K_RETURN)
    game.step(1 / 60)
    assert game.dialogue.state == DialogueState.WAITING
    wait_for_result(game)
    assert game.dialogue.state == DialogueState.ANSWERED
    assert game.dialogue.citations and game.stamps.has("Anaga")

    press(pygame.K_ESCAPE)
    game.step(1 / 60)
    assert not game.dialogue.is_open


def test_same_player_id_and_scene_sent(game: Any) -> None:
    for index in range(3):
        teleport(game, index)
        game.dialogue.open(game.npcs[index])
        request_id = game.api.send(game.player_id, "hola", game.npcs[index].zone,
                                   None, game.npcs[index].name)
        game.dialogue.mark_waiting(request_id, "hola")
        wait_for_result(game)
    assert {p["player_id"] for p in game.poster.payloads} == {"jugador-test"}
    assert [p["game_context"]["scene"] for p in game.poster.payloads] == ["Anaga", "Teide", "Santa Cruz"]
    assert game.stamps.complete


def test_error_response_gives_no_stamp() -> None:
    g = Game(api=ApiClient(poster=fake_poster(error="fallo")), player_id="p", skip_intro=True)
    g.dialogue.open(g.npcs[1])
    g.dialogue.mark_waiting(g.api.send("p", "hola", "Teide", None, g.npcs[1].name), "hola")
    wait_for_result(g)
    assert g.dialogue.state == DialogueState.ERROR and g.stamps.count == 0
    pygame.quit()


def test_slow_api_does_not_block_loop() -> None:
    g = Game(api=ApiClient(poster=fake_poster(delay=1.0)), player_id="p", skip_intro=True)
    g.dialogue.open(g.npcs[0])
    g.dialogue.mark_waiting(g.api.send("p", "hola", "Anaga", None, g.npcs[0].name), "hola")
    start = time.perf_counter()
    for _ in range(10):
        g.step(1 / 60)
    assert time.perf_counter() - start < 0.5, "los fotogramas no esperan a la red"
    assert g.dialogue.state == DialogueState.WAITING
    wait_for_result(g)
    pygame.quit()


def test_api_down_shows_useful_error() -> None:
    g = Game(api=ApiClient(url="http://127.0.0.1:9/chat", timeout=2.0), player_id="p", skip_intro=True)
    g.dialogue.open(g.npcs[2])
    g.dialogue.mark_waiting(g.api.send("p", "hola", "Santa Cruz", None, g.npcs[2].name), "hola")
    start = time.perf_counter()
    g.step(1 / 60)
    assert time.perf_counter() - start < 0.5
    wait_for_result(g, 5.0)
    assert g.dialogue.state == DialogueState.ERROR
    assert "API" in (g.dialogue.error or "")
    pygame.quit()


def test_game_never_imports_llm_libraries() -> None:
    forbidden = {"openai", "langchain", "langchain_openai", "pypdf", "backend", "numpy"}
    for path in GAME_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [(node.module or "").split(".")[0]]
            else:
                continue
            assert not forbidden & set(names), f"{path.name} importa {names}"


def test_story_intro_chapters_and_captain() -> None:
    from game.story import CHAPTERS, ENDING_PAGES, INTRO_PAGES

    g = Game(api=ApiClient(poster=fake_poster()), player_id="p")
    assert g.cutscene is not None and g.cutscene.pages == INTRO_PAGES
    for _ in INTRO_PAGES:
        press(pygame.K_RETURN)
    g.step(1 / 60)
    assert g.cutscene is None, "Enter recorre la introducción"

    assert g.captain.can_interact(g.player.rect), "la partida empieza junto a la capitana"
    press(pygame.K_e, "e")
    g.step(1 / 60)
    assert g.dialogue.state == DialogueState.STORY
    press(pygame.K_ESCAPE)
    g.step(1 / 60)
    assert not g.dialogue.is_open and g.api.pending == 0, "la capitana no llama a la API"

    for index in range(3):
        g.dialogue.open(g.npcs[index])
        g.dialogue.mark_waiting(g.api.send("p", "hola", g.npcs[index].zone, None,
                                           g.npcs[index].name), "hola")
        wait_for_result(g)
        assert g.cutscene is None, "el capítulo espera a que se cierre el diálogo"
        g.dialogue.close()
        g.step(1 / 60)
        assert g.cutscene is not None
        assert g.cutscene.pages[0] == CHAPTERS[g.npcs[index].zone]
        g.cutscene = None
    assert g.stamps.complete


def test_map_regions_follow_tenerife_geography(game: Any) -> None:
    from game.world import ZONES

    anaga, teide, santa_cruz, sur = (ZONES[z] for z in ("Anaga", "Teide", "Santa Cruz", "Los Cristianos"))
    assert anaga[0] > teide[0] and anaga[1] < teide[1], "Anaga al noreste del Teide"
    assert santa_cruz[1] > anaga[1] and santa_cruz[0] > teide[0], "Santa Cruz al pie de Anaga, al este"
    assert sur[1] > teide[1], "Los Cristianos en el sur"
    peak = [(c, r) for r, line in enumerate(game.world.layout) for c, ch in enumerate(line) if ch == "^"]
    assert all(teide[0] <= c < teide[0] + teide[2] and teide[1] <= r < teide[1] + teide[3] for c, r in peak)


def test_every_character_is_reachable_on_foot(game: Any) -> None:
    """Recorre el mapa desde la salida y comprueba que se llega a todos los personajes."""
    from collections import deque

    world = game.world
    start = (game.player.rect.centerx // TILE, game.player.rect.centery // TILE)
    seen, queue = {start}, deque([start])
    while queue:
        col, row = queue.popleft()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (col + dc, row + dr)
            if nxt not in seen and not world.is_solid_at(nxt[0] * TILE + 16, nxt[1] * TILE + 16):
                seen.add(nxt)
                queue.append(nxt)
    for npc in [*game.npcs, game.captain]:
        col, row = npc.tile
        neighbours = {(col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1), (col, row)}
        assert neighbours & seen, f"{npc.name} no es accesible"
