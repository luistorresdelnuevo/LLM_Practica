"""Mapa de Tenerife a escala aproximada (30 x 20 casillas).

El contorno se ha trazado a partir de coordenadas reales aproximadas: Teno al
noroeste, la península de Anaga al noreste, el Teide y Las Cañadas en el
centro-oeste, Santa Cruz en la costa este al pie de Anaga y la punta sur
(Los Cristianos, El Médano) abajo. Gráficos y personajes son originales.

Leyenda de casillas:
    ``~`` mar · ``s`` arena · ``.`` hierba · ``f`` bosque (transitable)
    ``T`` árbol · ``r`` roca · ``^`` cumbre nevada · ``l`` malpaís
    ``=`` calle · ``B`` edificio · ``a`` autopista · ``c`` coche · ``p`` palmera
Las casillas ``~``, ``T``, ``r``, ``^``, ``B``, ``c`` y ``p`` bloquean el paso.

El dibujo es 2.5D: cada casilla tiene una altura, las caras frontales de los
desniveles se pintan como acantilados y los objetos altos se devuelven como
«sprites» para ordenarlos por profundidad junto a los personajes.
"""

from __future__ import annotations

import math
import random
from typing import Callable

import pygame

from .render import draw_car, draw_house, draw_palm, draw_tree, mix, shade
from .settings import COLORS, MAP_COLS, MAP_ROWS, TILE

MAP_LAYOUT: list[str] = [
    "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
    "~~~~~~~~~~~~~~~~~~~~~fTffTfT~~",
    "~~~~~~~~~~~~~~~~~~sTfTfTfffTf~",
    "~~~~~~~~~~~~~~~~ss.faaaaaaaff~",
    "~~~~~~~~~~~~~~ss...fafTfTfTf~~",
    "~~~~~~~~~~sssT.....p=B=B=s~~~~",
    "~~~~~sssssaaaaaaaaaa=====~~~~~",
    "~~sffT...lllll..c..caB=B~~~~~~",
    "~~sfT...lllllll.....aas~~~~~~~",
    "~~~s...lllrrrlll...aas~~~~~~~~",
    "~~~~s..llr^^^rll..aas~~~~~~~~~",
    "~~~~s..lllrrrlll.aas~~~~~~~~~~",
    "~~~~~s..lllllla.aas~~~~~~~~~~~",
    "~~~~~~s.plllllaaas~~~~~~~~~~~~",
    "~~~~~~~s.p.c..aap~~~~~~~~~~~~~",
    "~~~~~~~~s....aas~~~~~~~~~~~~~~",
    "~~~~~~~~~s...ps~~~~~~~~~~~~~~~",
    "~~~~~~~~~~sss~~~~~~~~~~~~~~~~~",
    "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
    "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
]

SOLID_TILES = set("~Tr^Bcp")

# Altura de cada casilla en «pisos»; cada piso son ELEVATION píxeles.
TILE_HEIGHT = {"~": 0, "s": 1, ".": 1, "f": 1, "T": 1, "=": 1, "B": 1,
               "l": 2, "r": 3, "^": 4, "a": 1, "c": 1, "p": 1}
ELEVATION = 7

TILE_COLORS = {
    "~": COLORS["sea"],
    "s": (232, 210, 156),
    ".": (112, 178, 86),
    "f": (54, 128, 72),
    "T": (54, 128, 72),
    "r": (110, 92, 84),
    "^": (238, 240, 246),
    "l": (128, 96, 78),
    "=": (196, 188, 176),
    "B": (196, 188, 176),
    "a": (64, 66, 74),
    "c": (64, 66, 74),
    "p": (226, 204, 150),
}
CLIFF_COLORS = {
    "s": (196, 162, 108), ".": (126, 98, 64), "f": (98, 76, 52), "T": (98, 76, 52),
    "l": (88, 62, 50), "r": (72, 58, 54), "^": (150, 156, 176), "=": (150, 140, 128),
    "B": (150, 140, 128), "a": (44, 44, 50), "c": (44, 44, 50), "p": (196, 162, 108),
}

# Zonas turísticas definidas en casillas: (columna, fila, ancho, alto).
ZONES: dict[str, tuple[int, int, int, int]] = {
    "Anaga": (18, 1, 11, 4),
    "Teide": (6, 7, 11, 7),
    "Santa Cruz": (19, 5, 7, 3),
    "Los Cristianos": (8, 14, 8, 3),
}
ZONE_COLORS = {"Anaga": (60, 170, 90), "Teide": (220, 110, 60), "Santa Cruz": (90, 140, 230),
               "Los Cristianos": (200, 150, 60)}

PLAYER_START = (11 * TILE + TILE // 2, 15 * TILE + TILE // 2)

Sprite = tuple[float, Callable[[pygame.Surface], None]]


class World:
    """Mapa en casillas con colisiones, alturas y detección de zona."""

    def __init__(self, layout: list[str] | None = None) -> None:
        self.layout = layout or MAP_LAYOUT
        if len(self.layout) != MAP_ROWS or any(len(r) != MAP_COLS for r in self.layout):
            raise ValueError("El mapa debe medir MAP_COLS x MAP_ROWS casillas.")
        self.solids: list[pygame.Rect] = [
            pygame.Rect(col * TILE, row * TILE, TILE, TILE)
            for row, line in enumerate(self.layout)
            for col, char in enumerate(line)
            if char in SOLID_TILES
        ]
        self.bounds = pygame.Rect(0, 0, MAP_COLS * TILE, MAP_ROWS * TILE)
        self._zone_rects = {
            name: pygame.Rect(c * TILE, r * TILE, w * TILE, h * TILE)
            for name, (c, r, w, h) in ZONES.items()
        }
        self._terrain: pygame.Surface | None = None
        self._coast: list[tuple[int, int, str]] = []

    # ------------------------------------------------------------------
    # Consultas lógicas
    # ------------------------------------------------------------------
    def tile(self, col: int, row: int) -> str:
        """Carácter de la casilla; fuera del mapa se considera mar."""
        if 0 <= row < MAP_ROWS and 0 <= col < MAP_COLS:
            return self.layout[row][col]
        return "~"

    def is_solid_at(self, x: float, y: float) -> bool:
        """Indica si el punto en píxeles cae en una casilla bloqueante."""
        col, row = int(x // TILE), int(y // TILE)
        if not (0 <= row < MAP_ROWS and 0 <= col < MAP_COLS):
            return True
        return self.layout[row][col] in SOLID_TILES

    def ground_offset(self, x: float, y: float) -> int:
        """Desplazamiento vertical en píxeles del suelo bajo un punto."""
        return TILE_HEIGHT[self.tile(int(x // TILE), int(y // TILE))] * ELEVATION

    def zone_at(self, point: tuple[float, float]) -> str:
        """Devuelve la zona turística del punto o «Costa» si no hay ninguna."""
        for name, rect in self._zone_rects.items():
            if rect.collidepoint(point):
                return name
        return "Costa"

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def _build_terrain(self) -> pygame.Surface:
        """Pre-renderiza el relieve una vez: caras superiores y acantilados."""
        surf = pygame.Surface(self.bounds.size, pygame.SRCALPHA)
        rng = random.Random(7)
        for row in range(MAP_ROWS):
            for col in range(MAP_COLS):
                char = self.tile(col, row)
                if char == "~":
                    continue
                h = TILE_HEIGHT[char] * ELEVATION
                top = pygame.Rect(col * TILE, row * TILE - h, TILE, TILE)
                base = TILE_COLORS[char]
                # Variación suave por casilla para que no parezca una rejilla plana.
                base = shade(base, 0.95 + rng.random() * 0.1)
                pygame.draw.rect(surf, base, top)

                # Luz desde arriba a la izquierda.
                if TILE_HEIGHT[self.tile(col, row - 1)] < TILE_HEIGHT[char]:
                    pygame.draw.line(surf, shade(base, 1.18), top.topleft, (top.right - 1, top.top), 2)
                if TILE_HEIGHT[self.tile(col - 1, row)] < TILE_HEIGHT[char]:
                    pygame.draw.line(surf, shade(base, 1.1), top.topleft, (top.left, top.bottom - 1), 2)
                if TILE_HEIGHT[self.tile(col + 1, row)] < TILE_HEIGHT[char]:
                    pygame.draw.line(surf, shade(base, 0.82), (top.right - 2, top.top),
                                     (top.right - 2, top.bottom - 1), 2)

                self._decorate(surf, char, top, rng)

                # Cara frontal hasta la altura de la casilla de abajo.
                below = self.tile(col, row + 1)
                hb = TILE_HEIGHT[below] * ELEVATION
                if hb < h:
                    face = pygame.Rect(top.x, top.bottom, TILE, h - hb)
                    cliff = CLIFF_COLORS[char]
                    pygame.draw.rect(surf, cliff, face)
                    pygame.draw.line(surf, shade(cliff, 1.25), face.topleft, (face.right - 1, face.top))
                    for i in range(0, face.h, 4):
                        pygame.draw.line(surf, shade(cliff, 0.85), (face.x, face.y + i),
                                         (face.right - 1, face.y + i))
                    if below == "~":
                        self._coast.append((col, row + 1, "front"))
                for dc in (-1, 1):
                    if self.tile(col + dc, row) == "~":
                        self._coast.append((col + dc, row, "side"))
                if self.tile(col, row - 1) == "~":
                    self._coast.append((col, row - 1, "back"))
        return surf

    @staticmethod
    def _decorate(surf: pygame.Surface, char: str, top: pygame.Rect, rng: random.Random) -> None:
        """Texturas pequeñas: hierba, flores, arena, grietas y nieve."""
        if char == ".":
            for _ in range(3):
                x, y = top.x + rng.randint(4, 27), top.y + rng.randint(4, 27)
                pygame.draw.line(surf, (88, 150, 70), (x, y), (x - 1, y - 3))
                pygame.draw.line(surf, (88, 150, 70), (x, y), (x + 2, y - 3))
            if rng.random() < 0.18:
                color = rng.choice([(250, 236, 120), (250, 160, 190), (255, 255, 255)])
                pygame.draw.circle(surf, color, (top.x + rng.randint(6, 26), top.y + rng.randint(6, 26)), 2)
        elif char in "fT":
            for _ in range(2):
                pygame.draw.circle(surf, (42, 108, 60),
                                   (top.x + rng.randint(5, 27), top.y + rng.randint(5, 27)), 3)
        elif char == "s":
            for _ in range(4):
                pygame.draw.circle(surf, (214, 190, 138),
                                   (top.x + rng.randint(3, 29), top.y + rng.randint(3, 29)), 1)
        elif char == "l":
            x, y = top.x + rng.randint(4, 20), top.y + rng.randint(4, 20)
            pygame.draw.lines(surf, (96, 70, 58), False, [(x, y), (x + 5, y + 4), (x + 9, y + 2)], 2)
        elif char == "r":
            pygame.draw.circle(surf, (132, 112, 102), (top.x + 10, top.y + 12), 6)
            pygame.draw.circle(surf, (150, 130, 120), (top.x + 8, top.y + 10), 2)
        elif char == "^":
            pygame.draw.circle(surf, (210, 216, 232), (top.x + 18, top.y + 20), 7)
            pygame.draw.circle(surf, (255, 255, 255), (top.x + 12, top.y + 9), 3)
        elif char in "ac":
            pygame.draw.line(surf, (236, 196, 60), (top.x + 4, top.centery), (top.x + 12, top.centery), 2)
            pygame.draw.line(surf, (236, 196, 60), (top.x + 20, top.centery), (top.x + 28, top.centery), 2)
            pygame.draw.circle(surf, (78, 80, 88), (top.x + rng.randint(4, 28), top.y + rng.randint(4, 28)), 1)
        elif char in "=B":
            pygame.draw.line(surf, (176, 168, 156), (top.x, top.y + 16), (top.right, top.y + 16))
            pygame.draw.line(surf, (176, 168, 156), (top.x + 16, top.y), (top.x + 16, top.y + 16))

    def draw_water(self, surface: pygame.Surface, time_s: float) -> None:
        """Mar animado con brillos y espuma en la costa."""
        surface.fill((34, 96, 152))
        deep, shallow = (30, 86, 142), (56, 140, 190)
        for row in range(MAP_ROWS):
            for col in range(MAP_COLS):
                if self.tile(col, row) != "~":
                    continue
                near = min(abs(col - 15) / 15, 1)
                t = 0.5 + 0.5 * math.sin(time_s * 1.3 + col * 0.6 + row * 0.9)
                color = mix(shallow, deep, near * 0.7 + t * 0.3)
                pygame.draw.rect(surface, color, (col * TILE, row * TILE, TILE, TILE))
                phase = time_s * 2 + col * 1.7 + row * 2.3
                if math.sin(phase) > 0.85:
                    y = row * TILE + 12 + int(math.sin(phase * 0.5) * 4)
                    pygame.draw.line(surface, (170, 214, 236), (col * TILE + 8, y), (col * TILE + 20, y), 2)
        foam = (236, 246, 250)
        for col, row, kind in self._coast:
            wave = int(2 + 2 * math.sin(time_s * 2.5 + col + row))
            x, y = col * TILE, row * TILE
            if kind == "front":
                pygame.draw.line(surface, foam, (x, y + wave), (x + TILE, y + wave), 3)
            elif kind == "back":
                pygame.draw.line(surface, foam, (x, y + TILE - 9 - wave), (x + TILE, y + TILE - 9 - wave), 2)
            else:
                pygame.draw.circle(surface, foam, (x + TILE // 2, y + TILE // 2 + wave), 2)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, time_s: float) -> None:
        """Dibuja mar y relieve (los objetos altos van en ``sprites``)."""
        if self._terrain is None:
            self._terrain = self._build_terrain()
        self.draw_water(surface, time_s)
        surface.blit(self._terrain, (0, 0))

    def sprites(self, time_s: float) -> list[Sprite]:
        """Árboles y casas como (profundidad, función de dibujo)."""
        items: list[Sprite] = []
        for row, line in enumerate(self.layout):
            for col, char in enumerate(line):
                base_y = (row + 1) * TILE - TILE_HEIGHT[char] * ELEVATION - 4
                cx = col * TILE + TILE // 2
                if char == "T":
                    seed = col * 31 + row
                    items.append((base_y, lambda s, p=(cx, base_y), k=seed: draw_tree(s, p, k, time_s)))
                elif char == "c":
                    seed = col * 13 + row
                    items.append((base_y, lambda s, p=(cx, base_y), k=seed: draw_car(s, p, k)))
                elif char == "p":
                    seed = col * 5 + row
                    items.append((base_y, lambda s, p=(cx, base_y), k=seed: draw_palm(s, p, k, time_s)))
                elif char == "B":
                    seed = col * 7 + row * 3
                    items.append((base_y, lambda s, p=(cx, base_y), k=seed: draw_house(s, p, TILE - 4, k)))
        return items

    def draw_labels(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Carteles flotantes con el nombre de cada zona."""
        for name, rect in self._zone_rects.items():
            text = font.render(name.upper(), True, (255, 255, 255))
            box = text.get_rect(topleft=(rect.x + 6, rect.y - 10)).inflate(14, 6)
            pygame.draw.rect(surface, shade(ZONE_COLORS[name], 0.55), box.move(0, 2), border_radius=8)
            pygame.draw.rect(surface, ZONE_COLORS[name], box, border_radius=8)
            pygame.draw.rect(surface, (255, 255, 255), box, 1, border_radius=8)
            surface.blit(text, text.get_rect(center=box.center))
