"""Interfaz de estilo «crimen urbano»: radar, dinero, búsqueda, reloj y banners.

Inspirada en los juegos de mundo abierto, pero con diseño propio: no usa
logotipos, tipografías ni recursos de terceros.
"""

from __future__ import annotations

import math
from functools import lru_cache

import pygame

from .render import shade
from .settings import HEIGHT, MAP_COLS, MAP_ROWS, TILE, WIDTH

HUD_GREEN = (110, 196, 90)
HUD_BLUE = (120, 170, 230)
HUD_YELLOW = (250, 226, 120)


@lru_cache(maxsize=32)
def get_font(size: int, family: str = "impact,arial black,arial", bold: bool = False) -> pygame.font.Font:
    """Fuente en caché para no buscarla en cada fotograma."""
    return pygame.font.SysFont(family, size, bold=bold)


def outlined(surface: pygame.Surface, text: str, font: pygame.font.Font,
             color: tuple[int, int, int], pos: tuple[int, int], anchor: str = "topleft",
             outline: int = 2) -> pygame.Rect:
    """Texto con contorno negro, como en los marcadores de los juegos de calle."""
    rendered = font.render(text, True, color)
    border = font.render(text, True, (0, 0, 0))
    rect = rendered.get_rect(**{anchor: pos})
    for ox in range(-outline, outline + 1):
        for oy in range(-outline, outline + 1):
            if ox or oy:
                surface.blit(border, rect.move(ox, oy))
    surface.blit(rendered, rect)
    return rect


class Radar:
    """Minimapa circular de la isla con el jugador y los informantes."""

    RADIUS = 70
    SCALE = 5  # píxeles del radar por casilla

    def __init__(self, layout: list[str]) -> None:
        colors = {"~": (40, 70, 110), "s": (200, 186, 140), "a": (60, 60, 66), "c": (60, 60, 66),
                  "=": (150, 150, 150), "B": (170, 120, 100), "^": (240, 240, 240),
                  "r": (110, 92, 84), "l": (120, 90, 74), "p": (200, 186, 140)}
        self.map = pygame.Surface((MAP_COLS * self.SCALE, MAP_ROWS * self.SCALE))
        for row, line in enumerate(layout):
            for col, char in enumerate(line):
                color = colors.get(char, (90, 150, 80))
                pygame.draw.rect(self.map, color, (col * self.SCALE, row * self.SCALE,
                                                   self.SCALE, self.SCALE))
        size = self.RADIUS * 2
        self.mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.mask, (255, 255, 255, 255), (self.RADIUS, self.RADIUS), self.RADIUS)

    def draw(self, surface: pygame.Surface, player_pos: tuple[int, int],
             blips: list[tuple[tuple[int, int], tuple[int, int, int]]], time_s: float) -> None:
        """Dibuja el radar abajo a la izquierda, centrado en el jugador."""
        r = self.RADIUS
        center = (24 + r, HEIGHT - 24 - r)
        scale = self.SCALE / TILE
        view = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        view.fill((30, 50, 80, 255))
        px, py = player_pos[0] * scale, player_pos[1] * scale
        view.blit(self.map, (r - px, r - py))
        for (bx, by), color in blips:
            dx, dy = bx * scale - px, by * scale - py
            dist = math.hypot(dx, dy)
            if dist > r - 8:
                dx, dy = dx / dist * (r - 8), dy / dist * (r - 8)
            pygame.draw.rect(view, (0, 0, 0), (r + dx - 5, r + dy - 5, 10, 10))
            pygame.draw.rect(view, color, (r + dx - 4, r + dy - 4, 8, 8))
        view.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        pygame.draw.circle(surface, (0, 0, 0), (center[0] + 2, center[1] + 3), r + 4)
        surface.blit(view, (center[0] - r, center[1] - r))
        pygame.draw.circle(surface, (16, 16, 20), center, r + 3, 5)
        pygame.draw.circle(surface, (200, 200, 200), center, r + 1, 1)
        arrow = [(center[0], center[1] - 7), (center[0] - 5, center[1] + 5), (center[0], center[1] + 2),
                 (center[0] + 5, center[1] + 5)]
        pygame.draw.polygon(surface, (255, 255, 255), arrow)
        pygame.draw.polygon(surface, (0, 0, 0), arrow, 1)
        outlined(surface, "N", get_font(16), (255, 255, 255), (center[0], center[1] - r + 2), "midtop")


class Hud:
    """Marcador superior derecho, banners y avisos."""

    def __init__(self) -> None:
        self.money_shown = 0.0
        self.banner: tuple[str, str, float] | None = None
        self.zone_name = ""
        self.zone_until = 0.0

    def show_banner(self, title: str, subtitle: str, time_s: float) -> None:
        """Banner grande en el centro durante unos segundos."""
        self.banner = (title, subtitle, time_s + 4.0)

    def show_zone(self, name: str, time_s: float) -> None:
        """Nombre de la zona al entrar, abajo a la derecha."""
        self.zone_name, self.zone_until = name, time_s + 3.0

    def draw(self, surface: pygame.Surface, *, money: int, wanted: int, time_s: float,
             objective: str, show_objective: bool, pending: bool) -> None:
        """Dibuja reloj, dinero, estrellas, objetivo y banners."""
        hours = (3 + int((12 + time_s) // 60)) % 24
        minutes = int(12 + time_s) % 60
        outlined(surface, f"{hours:02d}:{minutes:02d}", get_font(30), (240, 240, 240),
                 (20, 14), "topleft")

        self.money_shown += (money - self.money_shown) * 0.08
        outlined(surface, f"${int(round(self.money_shown)):08d}", get_font(32), HUD_GREEN,
                 (20, 50), "topleft")

        for i in range(5):
            cx = 34 + i * 30
            cy = 106
            lit = i < wanted
            blink = lit and wanted >= 5 and int(time_s * 4) % 2 == 0
            color = (250, 250, 250) if blink else (HUD_YELLOW if lit else (70, 70, 70))
            pts = []
            for k in range(10):
                rr = 12 if k % 2 == 0 else 5
                ang = -math.pi / 2 + k * math.pi / 5
                pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
            pygame.draw.polygon(surface, (0, 0, 0), [(x + 1, y + 2) for x, y in pts])
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, (0, 0, 0), pts, 1)

        if show_objective:
            text = objective + ("   ·   consultando al informante..." if pending else "")
            outlined(surface, text, get_font(18, "arial", True), HUD_YELLOW,
                     (WIDTH // 2 + 70, HEIGHT - 22), "midbottom")

        if self.zone_name and time_s < self.zone_until:
            alpha_t = min(1.0, (self.zone_until - time_s) / 0.6)
            color = tuple(int(c * alpha_t) for c in (255, 255, 255))
            outlined(surface, self.zone_name.upper(), get_font(44), color,  # type: ignore[arg-type]
                     (WIDTH - 24, HEIGHT - 50), "bottomright", 3)

        if self.banner and time_s < self.banner[2]:
            title, subtitle, _ = self.banner
            pulse = 1 + 0.04 * math.sin(time_s * 8)
            font = get_font(int(52 * pulse))
            outlined(surface, title, font, HUD_YELLOW, (WIDTH // 2, 150), "center", 3)
            outlined(surface, subtitle, get_font(30), shade(HUD_GREEN, 1.1), (WIDTH // 2, 196),
                     "center", 2)
