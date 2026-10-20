"""Personaje controlable con WASD o flechas."""

from __future__ import annotations

import math

import pygame

from .render import Palette, draw_character
from .settings import PLAYER_SIZE, PLAYER_SPEED
from .world import World


PLAYER_PALETTE = Palette(shirt=(236, 236, 240), pants=(40, 50, 80), skin=(232, 190, 150),
                         hair=(30, 26, 24), hat=None, accent=(200, 60, 50),
                         sunglasses=True, jacket=(110, 64, 36))


def read_direction(keys: pygame.key.ScancodeWrapper) -> pygame.Vector2:
    """Convierte el estado del teclado en una dirección normalizada."""
    direction = pygame.Vector2(
        (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT]),
        (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP]),
    )
    if direction.length_squared() > 0:
        direction = direction.normalize()
    return direction


class Player:
    """Jugador con colisión por ejes contra las casillas sólidas."""

    def __init__(self, x: float, y: float) -> None:
        self.pos = pygame.Vector2(x, y)
        self.rect = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
        self.rect.center = (round(x), round(y))
        self.facing = (0.0, 1.0)
        self.walk_phase = 0.0
        self.moving = False

    def _collides(self, world: World, rect: pygame.Rect) -> bool:
        corners = (rect.topleft, (rect.right - 1, rect.top),
                   (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
        return any(world.is_solid_at(x, y) for x, y in corners)

    def move(self, direction: pygame.Vector2, dt: float, world: World) -> None:
        """Avanza en cada eje por separado para deslizar junto a los muros."""
        step = direction * PLAYER_SPEED * dt
        self.moving = direction.length_squared() > 0
        if self.moving:
            self.facing = (direction.x, direction.y)
            self.walk_phase += dt * 14
        for axis in (0, 1):
            if step[axis] == 0:
                continue
            candidate = self.pos.copy()
            candidate[axis] += step[axis]
            rect = self.rect.copy()
            rect.center = (round(candidate.x), round(candidate.y))
            if world.bounds.contains(rect) and not self._collides(world, rect):
                self.pos = candidate
                self.rect = rect

    def draw(self, surface: pygame.Surface, ground_offset: int, time_s: float) -> None:
        """Dibuja al viajero con sombra, paso alternado y respiración."""
        bob = abs(math.sin(self.walk_phase)) * 2 if self.moving else math.sin(time_s * 3) * 0.6
        foot = (self.rect.centerx, self.rect.bottom - ground_offset)
        draw_character(surface, foot, PLAYER_PALETTE, bob=bob,
                       step=self.walk_phase if self.moving else 0.0, facing=self.facing)
