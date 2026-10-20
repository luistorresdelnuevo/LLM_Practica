"""Guías turísticos originales de cada zona."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from .render import Palette, draw_character, draw_shadow, shade
from .settings import INTERACT_DISTANCE, TILE


@dataclass
class NPC:
    """Personaje con el que se conversa pulsando E."""

    name: str
    zone: str
    tile: tuple[int, int]
    color: tuple[int, int, int]
    greeting: str
    palette: Palette
    rect: pygame.Rect = field(init=False)

    def __post_init__(self) -> None:
        col, row = self.tile
        self.rect = pygame.Rect(0, 0, 24, 24)
        self.rect.center = (col * TILE + TILE // 2, row * TILE + TILE // 2)

    def can_interact(self, player_rect: pygame.Rect) -> bool:
        """El jugador está lo bastante cerca para hablar."""
        dx = self.rect.centerx - player_rect.centerx
        dy = self.rect.centery - player_rect.centery
        return math.hypot(dx, dy) <= INTERACT_DISTANCE

    def facing_towards(self, point: tuple[float, float]) -> tuple[float, float]:
        """Dirección normalizada hacia un punto (para mirar al jugador)."""
        dx, dy = point[0] - self.rect.centerx, point[1] - self.rect.centery
        length = math.hypot(dx, dy) or 1.0
        return dx / length, dy / length

    def draw(self, surface: pygame.Surface, time_s: float, ground_offset: int,
             look_at: tuple[float, float] | None = None) -> None:
        """Dibuja el cuerpo del guía mirando al jugador si está cerca."""
        foot = (self.rect.centerx, self.rect.bottom - ground_offset)
        facing = self.facing_towards(look_at) if look_at else (0.0, 1.0)
        bob = math.sin(time_s * 2.4 + self.tile[0]) * 1.0

        # Aro de color en el suelo para distinguir a los guías.
        ring = pygame.Rect(0, 0, 34, 14)
        ring.center = (round(foot[0]), round(foot[1]))
        pygame.draw.ellipse(surface, shade(self.color, 1.2), ring, 2)
        draw_character(surface, foot, self.palette, bob=bob, facing=facing)

    def draw_overlay(self, surface: pygame.Surface, font: pygame.font.Font, highlighted: bool,
                     has_stamp: bool, time_s: float, ground_offset: int) -> None:
        """Nombre, sello e indicador: se dibujan encima de todos los objetos."""
        foot = (self.rect.centerx, self.rect.bottom - ground_offset)
        name = font.render(self.name, True, (255, 255, 255))
        plate = name.get_rect(midtop=(self.rect.centerx, foot[1] + 6)).inflate(10, 4)
        pygame.draw.rect(surface, shade(self.color, 0.45), plate, border_radius=6)
        surface.blit(name, name.get_rect(center=plate.center))

        if has_stamp:
            star_c = (self.rect.centerx + 16, foot[1] - 48)
            draw_star(surface, star_c, 7, (255, 220, 90))

        if highlighted:
            jump = abs(math.sin(time_s * 5)) * 5
            bubble = pygame.Rect(0, 0, 30, 26)
            bubble.midbottom = (self.rect.centerx, foot[1] - 54 - jump)
            draw_shadow(surface, (bubble.centerx, foot[1] - 2), 18, 6, 60)
            pygame.draw.rect(surface, (40, 40, 60), bubble.move(0, 2), border_radius=8)
            pygame.draw.rect(surface, (255, 255, 255), bubble, border_radius=8)
            pygame.draw.polygon(surface, (255, 255, 255),
                                [(bubble.centerx - 5, bubble.bottom - 1),
                                 (bubble.centerx + 5, bubble.bottom - 1),
                                 (bubble.centerx, bubble.bottom + 6)])
            key = font.render("E", True, shade(self.color, 0.6))
            surface.blit(key, key.get_rect(center=bubble.center))

    def draw_portrait(self, surface: pygame.Surface, center: tuple[int, int], time_s: float) -> None:
        """Retrato grande para la ventana de diálogo."""
        frame = pygame.Rect(0, 0, 96, 96)
        frame.center = center
        pygame.draw.rect(surface, shade(self.color, 0.45), frame.move(0, 3), border_radius=14)
        pygame.draw.rect(surface, shade(self.color, 1.15), frame, border_radius=14)
        inner = frame.inflate(-8, -8)
        pygame.draw.rect(surface, (250, 246, 232), inner, border_radius=10)
        clip = surface.get_clip()
        surface.set_clip(inner)
        bob = math.sin(time_s * 2.4) * 1.5
        draw_character(surface, (inner.centerx, inner.bottom + 26), self.palette,
                       scale=2.6, bob=bob, shadow=False)
        surface.set_clip(clip)


def draw_star(surface: pygame.Surface, center: tuple[float, float], radius: int,
              color: tuple[int, int, int]) -> None:
    """Estrella de cinco puntas (sello conseguido)."""
    cx, cy = center
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        angle = -math.pi / 2 + i * math.pi / 5
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    pygame.draw.polygon(surface, shade(color, 0.6), [(x + 1, y + 1) for x, y in points])
    pygame.draw.polygon(surface, color, points)


def create_guides() -> list[NPC]:
    """Crea los tres informantes del caso (responden mediante la API)."""
    return [
        NPC("El Lagarto", "Anaga", (26, 2), (70, 180, 90),
            "Psst... aquí arriba, entre la laurisilva. Si vienes por lo de El Faro, primero "
            "pregúntame algo del monte. Senderos, miradores, playas. Luego hablamos.",
            Palette(shirt=(60, 150, 70), pants=(50, 60, 70), skin=(214, 170, 130),
                    hair=(30, 30, 30), hat=(40, 110, 50), accent=(20, 20, 20),
                    sunglasses=True)),
        NPC("Doña Ceniza", "Teide", (14, 11), (220, 110, 60),
            "Desde aquí arriba lo veo todo, detective. Todo. Pero mi memoria va mejor si me "
            "preguntas por el volcán... o por el tiempo que hará mañana.",
            Palette(shirt=(110, 104, 110), pants=(60, 50, 50), skin=(222, 180, 150),
                    hair=(236, 236, 240), hat=(30, 30, 36), accent=(200, 70, 50),
                    jacket=(70, 60, 64))),
        NPC("Toni Grúas", "Santa Cruz", (22, 6), (90, 140, 230),
            "En el muelle nadie habla con la pasma, detective. Pero si me pides una ruta por "
            "la ciudad, igual me acuerdo de algo.",
            Palette(shirt=(250, 140, 30), pants=(40, 60, 110), skin=(236, 196, 160),
                    hair=(60, 40, 30), hat=(250, 210, 40), accent=(240, 240, 240),
                    chain=True, sunglasses=True)),
    ]


def create_captain() -> NPC:
    """Inspectora Salazar: narradora del caso, no usa la API."""
    return NPC("Insp. Salazar", "Los Cristianos", (12, 15), (60, 90, 170), "",
               Palette(shirt=(50, 70, 130), pants=(30, 34, 50), skin=(220, 176, 140),
                       hair=(40, 30, 26), hat=(24, 30, 60), accent=(230, 200, 80),
                       sunglasses=True, jacket=(30, 40, 80)))
