"""Punto de entrada de «Tenerife Noir · El caso del Faro».

Ejecución (desde ``brujula_tenerife``)::

    python -m game.main

El juego solo se comunica con la API local mediante HTTP.
"""

from __future__ import annotations

import pygame

from .api_client import ApiClient
from .dialogue import Dialogue
from .cutscene import Cutscene
from .hud import Hud, Radar, get_font
from .npc import NPC, create_captain, create_guides
from .render import make_vignette, vertical_gradient
from .player import Player, read_direction
from .quest import StampBook
from .story import CLUE_REWARD, CHAPTERS, ENDING_PAGES, INTRO_PAGES, Page, handler_text, objective
from .settings import FPS, HEIGHT, PLAYER_ID, TITLE, WIDTH
from .world import PLAYER_START, World


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Fuente del sistema con acentos; usa la de Pygame si no existe."""
    try:
        return pygame.font.SysFont("segoeui,arial", size, bold=bold)
    except Exception:  # noqa: BLE001
        return pygame.font.Font(None, size + 6)


class Game:
    """Bucle principal: entrada, actualización y dibujo."""

    def __init__(self, api: ApiClient | None = None, player_id: str = PLAYER_ID,
                 skip_intro: bool = False) -> None:
        pygame.init()
        get_font.cache_clear()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = load_font(20, bold=True)
        self.small = load_font(17)
        self.label_font = load_font(14, bold=True)
        self.title_font = load_font(28, bold=True)

        self.player_id = player_id
        self.world = World()
        self.player = Player(*PLAYER_START)
        self.npcs: list[NPC] = create_guides()
        self.captain = create_captain()
        self.cutscene: Cutscene | None = None if skip_intro else Cutscene(INTRO_PAGES, set())
        self.page_queue: list[Page] = []
        self.dialogue = Dialogue()
        self.api = api or ApiClient()
        self.stamps = StampBook()
        self.toast = ""
        self.toast_until = 0.0
        self.time_s = 0.0
        self.running = True
        self._vignette = make_vignette((WIDTH, HEIGHT), strength=150)
        # Filtro de color de atardecer: cielo cálido arriba y sombras violetas abajo.
        self._grade = vertical_gradient((WIDTH, HEIGHT), (255, 150, 60), (90, 40, 140), alpha=38)
        self.hud = Hud()
        self.radar = Radar(self.world.layout)
        self.money = 0
        self.last_zone = ""
        pygame.key.start_text_input()

    # ------------------------------------------------------------------
    def nearby_npc(self) -> NPC | None:
        """Guía al alcance del jugador, si lo hay."""
        candidates = [*self.npcs, self.captain]
        return next((n for n in candidates if n.can_interact(self.player.rect)), None)

    @property
    def scene(self) -> str:
        """Zona actual del jugador."""
        return self.world.zone_at(self.player.rect.center)

    def show_toast(self, text: str, seconds: float = 3.0) -> None:
        """Mensaje temporal en la parte superior."""
        self.toast, self.toast_until = text, self.time_s + seconds

    # ------------------------------------------------------------------
    def handle_events(self) -> None:
        """Procesa la cola de eventos de Pygame."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif self.cutscene is not None:
                self.cutscene.handle_event(event)
                if self.cutscene.finished:
                    self.cutscene = None
            elif self.dialogue.is_open:
                question = self.dialogue.handle_event(event)
                if question and self.dialogue.npc is not None:
                    npc = self.dialogue.npc
                    request_id = self.api.send(self.player_id, question, npc.zone,
                                               objective(self.stamps.stamps)[:80],
                                               npc.name)
                    self.dialogue.mark_waiting(request_id, question)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                npc = self.nearby_npc()
                if npc is self.captain:
                    self.dialogue.open_story(npc, handler_text(self.stamps.stamps))
                elif npc is not None:
                    self.dialogue.open(npc)

    def update(self, dt: float) -> None:
        """Mueve al jugador y recoge respuestas sin bloquear."""
        self.time_s += dt
        if self.dialogue.is_open or self.cutscene is not None:
            self.player.moving = False
        else:
            self.player.move(read_direction(pygame.key.get_pressed()), dt, self.world)

        result = self.api.poll()
        while result is not None:
            self.dialogue.apply_result(result)
            if result.error is None and result.answer:
                zone = next((n.zone for n in self.npcs if n.name == result.npc_name), "")
                if self.stamps.award(zone):
                    self.page_queue.append(CHAPTERS[zone])
                    if self.stamps.complete:
                        self.page_queue.extend(ENDING_PAGES)
                    self.money += CLUE_REWARD
                    if self.stamps.complete:
                        self.hud.show_banner("¡CASO RESUELTO!", f"+${CLUE_REWARD}   ·   Cierra con Esc",
                                             self.time_s)
                    else:
                        self.hud.show_banner("¡PISTA CONSEGUIDA!",
                                             f"+${CLUE_REWARD}   ·   {self.stamps.count}/3   ·   Esc",
                                             self.time_s)
            result = self.api.poll()

        zone = self.scene
        if zone != self.last_zone:
            self.last_zone = zone
            if zone != "Costa":
                self.hud.show_zone(zone, self.time_s)

        # Los capítulos se narran al cerrar el diálogo, para poder leer la respuesta.
        if self.page_queue and not self.dialogue.is_open and self.cutscene is None:
            self.cutscene = Cutscene(self.page_queue, self.stamps.stamps)
            self.page_queue = []

    # ------------------------------------------------------------------
    def draw_hud(self) -> None:
        """Radar, reloj, dinero, nivel de búsqueda, objetivo y banners."""
        blips = [(n.rect.center, n.color) for n in self.npcs if not self.stamps.has(n.zone)]
        blips.append((self.captain.rect.center, (230, 230, 230)))
        self.radar.draw(self.screen, self.player.rect.center, blips, self.time_s)
        wanted = self.stamps.count + (2 if self.stamps.complete else 0)
        self.hud.draw(self.screen, money=self.money, wanted=wanted, time_s=self.time_s,
                      objective=objective(self.stamps.stamps),
                      show_objective=not self.dialogue.is_open and self.cutscene is None,
                      pending=bool(self.api.pending))

    def draw(self) -> None:
        """Dibuja el fotograma: relieve, objetos por profundidad, interfaz."""
        self.world.draw(self.screen, self.label_font, self.time_s)
        near = None if self.dialogue.is_open or self.cutscene else self.nearby_npc()
        sprites = self.world.sprites(self.time_s)
        player_c = self.player.rect.center
        for npc in [*self.npcs, self.captain]:
            offset = self.world.ground_offset(*npc.rect.center)
            look = player_c if npc.can_interact(self.player.rect) or npc is self.dialogue.npc else None
            sprites.append((npc.rect.bottom - offset,
                            lambda s, n=npc, o=offset, l=look: n.draw(s, self.time_s, o, l)))
        p_off = self.world.ground_offset(*player_c)
        sprites.append((self.player.rect.bottom - p_off,
                        lambda s: self.player.draw(s, p_off, self.time_s)))
        for _, painter in sorted(sprites, key=lambda item: item[0]):
            painter(self.screen)
        for npc in [*self.npcs, self.captain]:
            npc.draw_overlay(self.screen, self.label_font, npc is near, self.stamps.has(npc.zone),
                             self.time_s, self.world.ground_offset(*npc.rect.center))
        self.screen.blit(self._grade, (0, 0))
        self.screen.blit(self._vignette, (0, 0))
        self.draw_hud()
        self.dialogue.draw(self.screen, self.font, self.small, self.time_s)
        if self.cutscene is not None:
            self.cutscene.draw(self.screen, self.title_font, self.small, self.time_s)
        pygame.display.flip()

    def step(self, dt: float) -> None:
        """Un fotograma completo; útil también en las pruebas."""
        self.handle_events()
        self.update(dt)
        self.draw()

    def run(self) -> None:
        """Bucle principal a ``FPS`` fotogramas por segundo."""
        while self.running:
            self.step(self.clock.tick(FPS) / 1000)
        pygame.quit()


def main() -> None:
    """Arranca el juego."""
    Game().run()


if __name__ == "__main__":
    main()
