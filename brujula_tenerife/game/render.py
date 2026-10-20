"""Utilidades de dibujo 2.5D con primitivas de Pygame (sin imágenes externas).

El estilo imita la perspectiva cenital inclinada de las consolas portátiles:
los objetos altos se extruyen hacia arriba, proyectan sombra y se ordenan por
profundidad según su base.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import pygame

Color = tuple[int, int, int]


def shade(color: Color, factor: float) -> Color:
    """Aclara (>1) u oscurece (<1) un color."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)  # type: ignore[return-value]


def mix(a: Color, b: Color, t: float) -> Color:
    """Interpola linealmente entre dos colores."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


@lru_cache(maxsize=64)
def _shadow_surface(width: int, height: int, alpha: int) -> pygame.Surface:
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (0, 0, 0, alpha), surf.get_rect())
    return surf


def draw_shadow(surface: pygame.Surface, center: tuple[float, float],
                width: int, height: int, alpha: int = 90) -> None:
    """Sombra elíptica semitransparente."""
    shadow = _shadow_surface(width, height, alpha)
    surface.blit(shadow, shadow.get_rect(center=(round(center[0]), round(center[1]))))


def vertical_gradient(size: tuple[int, int], top: Color, bottom: Color,
                      alpha: int = 255) -> pygame.Surface:
    """Superficie con degradado vertical."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(size[1]):
        color = mix(top, bottom, y / max(1, size[1] - 1))
        pygame.draw.line(surf, (*color, alpha), (0, y), (size[0], y))
    return surf


def make_vignette(size: tuple[int, int], strength: int = 110) -> pygame.Surface:
    """Oscurece suavemente los bordes de la pantalla."""
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    steps = 40
    for i in range(steps):
        t = 1 - i / steps
        alpha = int(strength * t ** 2.2)
        pygame.draw.rect(surf, (10, 14, 30, alpha),
                         (i * 3, i * 3, w - i * 6, h - i * 6), 3, border_radius=40)
    return surf


@dataclass(frozen=True)
class Palette:
    """Colores de un personaje chibi."""

    shirt: Color
    pants: Color
    skin: Color
    hair: Color
    hat: Color | None = None
    accent: Color = (255, 255, 255)
    sunglasses: bool = False
    chain: bool = False
    jacket: Color | None = None


def draw_character(surface: pygame.Surface, foot: tuple[float, float], palette: Palette,
                   *, scale: float = 1.0, bob: float = 0.0, step: float = 0.0,
                   facing: tuple[float, float] = (0.0, 1.0), shadow: bool = True) -> None:
    """Dibuja un personaje cabezón con volumen; ``foot`` es el punto de apoyo."""
    fx, fy = foot
    s = scale
    if shadow:
        draw_shadow(surface, (fx, fy), int(26 * s), int(10 * s))

    lift = bob
    # Piernas con paso alternado.
    leg_off = math.sin(step) * 3 * s
    for side, off in ((-1, leg_off), (1, -leg_off)):
        leg = pygame.Rect(0, 0, int(6 * s), int(8 * s))
        leg.midbottom = (round(fx + side * 4 * s), round(fy - 1 + min(0, off)))
        pygame.draw.rect(surface, shade(palette.pants, 0.8), leg, border_radius=int(2 * s))

    # Cuerpo.
    body = pygame.Rect(0, 0, int(18 * s), int(14 * s))
    body.midbottom = (round(fx), round(fy - 6 * s - lift))
    pygame.draw.rect(surface, shade(palette.shirt, 0.7), body.move(0, 1), border_radius=int(6 * s))
    pygame.draw.rect(surface, palette.shirt, body, border_radius=int(6 * s))
    pygame.draw.rect(surface, shade(palette.shirt, 1.25),
                     (body.x + 3 * s, body.y + 2 * s, 5 * s, 6 * s), border_radius=int(2 * s))
    if palette.jacket is not None:
        for side in (-1, 1):
            flap = pygame.Rect(0, 0, round(6 * s), body.h)
            flap.midtop = (round(fx + side * 6 * s), body.top)
            pygame.draw.rect(surface, palette.jacket, flap, border_radius=int(3 * s))
    if palette.chain:
        pygame.draw.arc(surface, (250, 206, 60),
                        (body.centerx - 6 * s, body.top - 4 * s, 12 * s, 10 * s), 3.4, 6.0, max(1, round(2 * s)))
    # Brazos.
    arm = math.sin(step) * 2 * s
    for side, off in ((-1, arm), (1, -arm)):
        pygame.draw.circle(surface, palette.skin,
                           (round(fx + side * 10 * s), round(body.centery + 2 * s + off)), round(3 * s))

    # Cabeza grande.
    head_c = (fx, body.top - 9 * s)
    r = 12 * s
    pygame.draw.circle(surface, shade(palette.skin, 0.75), (round(head_c[0]), round(head_c[1] + 1.5 * s)), round(r))
    pygame.draw.circle(surface, palette.skin, (round(head_c[0]), round(head_c[1])), round(r))
    # Pelo (parte superior y trasera).
    hair_c = (round(head_c[0]), round(head_c[1] - 1 * s))
    pygame.draw.circle(surface, palette.hair, hair_c, round(r + 1),
                       draw_top_left=True, draw_top_right=True)
    pygame.draw.rect(surface, palette.hair, (hair_c[0] - r - 1, hair_c[1] - 1, 4 * s, 7 * s),
                     border_radius=int(2 * s))
    pygame.draw.rect(surface, palette.hair, (hair_c[0] + r + 1 - 4 * s, hair_c[1] - 1, 4 * s, 7 * s),
                     border_radius=int(2 * s))

    # Ojos según la dirección.
    dx, dy = facing
    if dy >= -0.3:
        ex = dx * 4 * s
        for side in (-1, 1):
            eye = (round(head_c[0] + side * 4.5 * s + ex), round(head_c[1] + 2 * s + max(0, dy) * s))
            pygame.draw.circle(surface, (30, 30, 40), eye, max(1, round(2 * s)))
            pygame.draw.circle(surface, (255, 255, 255), (eye[0] - 1, eye[1] - 1), max(1, round(0.7 * s)))
        blush = shade(palette.skin, 0.9)
        for side in (-1, 1):
            pygame.draw.circle(surface, blush, (round(head_c[0] + side * 8 * s), round(head_c[1] + 5 * s)), round(2 * s))

    if palette.sunglasses and dy >= -0.3:
        ex = dx * 3 * s
        glasses_y = round(head_c[1] + 1 * s)
        for side in (-1, 1):
            lens = pygame.Rect(0, 0, round(8 * s), round(5 * s))
            lens.center = (round(head_c[0] + side * 4.5 * s + ex), glasses_y)
            pygame.draw.rect(surface, (16, 16, 22), lens, border_radius=int(2 * s))
            pygame.draw.line(surface, (120, 140, 170), (lens.x + 1, lens.y + 1),
                             (lens.x + 3 * s, lens.y + 1))
        pygame.draw.line(surface, (16, 16, 22), (round(head_c[0] - 1 * s + ex), glasses_y),
                         (round(head_c[0] + 1 * s + ex), glasses_y), max(1, round(s)))

    # Sombrero o gorra.
    if palette.hat is not None:
        brim = pygame.Rect(0, 0, round(2 * r + 8 * s), round(7 * s))
        brim.center = (round(head_c[0]), round(head_c[1] - 6 * s))
        pygame.draw.ellipse(surface, shade(palette.hat, 0.75), brim)
        crown = pygame.Rect(0, 0, round(r * 1.3), round(9 * s))
        crown.midbottom = (round(head_c[0]), brim.centery + 1)
        pygame.draw.rect(surface, palette.hat, crown, border_radius=int(4 * s))
        pygame.draw.rect(surface, palette.accent, (crown.x, crown.bottom - 3 * s, crown.w, 2 * s))

    # Brillo de la cabeza.
    pygame.draw.circle(surface, shade(palette.skin, 1.18),
                       (round(head_c[0] - 5 * s), round(head_c[1] - 3 * s)), max(1, round(2.5 * s)))


def draw_tree(surface: pygame.Surface, base: tuple[int, int], seed: int, time_s: float) -> None:
    """Árbol de laurisilva con copa en capas y balanceo leve."""
    bx, by = base
    sway = math.sin(time_s * 1.5 + seed) * 1.2
    draw_shadow(surface, (bx + 4, by - 2), 34, 13, 80)
    pygame.draw.rect(surface, (92, 62, 40), (bx - 3, by - 16, 7, 16), border_radius=2)
    pygame.draw.rect(surface, (120, 84, 54), (bx - 3, by - 16, 3, 16), border_radius=2)
    dark, mid, light = (22, 82, 46), (36, 120, 62), (78, 164, 86)
    pygame.draw.circle(surface, dark, (round(bx + sway), by - 24), 15)
    pygame.draw.circle(surface, mid, (round(bx - 5 + sway), by - 30), 12)
    pygame.draw.circle(surface, mid, (round(bx + 6 + sway), by - 28), 11)
    pygame.draw.circle(surface, light, (round(bx - 4 + sway * 1.3), by - 36), 8)
    pygame.draw.circle(surface, (130, 200, 120), (round(bx - 7 + sway * 1.3), by - 39), 3)


def draw_house(surface: pygame.Surface, base: tuple[int, int], width: int, seed: int) -> None:
    """Casa canaria extruida: fachada encalada, balcón de madera y tejado."""
    bx, by = base
    wall_h, roof_h = 22, 12
    draw_shadow(surface, (bx + 5, by - 1), width + 10, 12, 90)
    facade_colors = [(244, 236, 220), (240, 214, 160), (232, 186, 160), (206, 222, 236)]
    facade = facade_colors[seed % len(facade_colors)]
    wall = pygame.Rect(0, 0, width, wall_h)
    wall.midbottom = (bx, by)
    pygame.draw.rect(surface, shade(facade, 0.82), wall)
    pygame.draw.rect(surface, facade, wall.inflate(-4, 0).move(-2, 0))
    # Puerta y ventanas con balcón de madera.
    pygame.draw.rect(surface, (110, 70, 44), (bx - 3, by - 11, 7, 11), border_top_left_radius=3,
                     border_top_right_radius=3)
    for side in (-1, 1):
        win = pygame.Rect(0, 0, 6, 6)
        win.center = (bx + side * (width // 2 - 6), by - 14)
        pygame.draw.rect(surface, (70, 120, 160), win)
        pygame.draw.rect(surface, (255, 255, 255), (win.x, win.y, 2, 2))
    pygame.draw.rect(surface, (122, 80, 46), (wall.x + 2, by - 9, width - 4, 2))
    # Tejado a dos aguas visto desde arriba.
    top = wall.top
    roof = [(wall.left - 3, top), (wall.right + 3, top), (wall.right - 2, top - roof_h),
            (wall.left + 2, top - roof_h)]
    pygame.draw.polygon(surface, (164, 64, 50), roof)
    pygame.draw.polygon(surface, (196, 90, 68),
                        [(wall.left - 3, top), (bx, top), (bx, top - roof_h), (wall.left + 2, top - roof_h)])
    for i in range(1, 4):
        y = top - i * roof_h // 4
        pygame.draw.line(surface, (140, 52, 42), (wall.left, y), (wall.right, y), 1)


CAR_COLORS = [(196, 40, 40), (30, 30, 36), (230, 230, 236), (40, 90, 170), (230, 170, 40)]


def draw_car(surface: pygame.Surface, base: tuple[int, int], seed: int) -> None:
    """Coche aparcado visto desde arriba con perspectiva inclinada."""
    bx, by = base
    color = CAR_COLORS[seed % len(CAR_COLORS)]
    draw_shadow(surface, (bx + 3, by - 2), 38, 14, 110)
    body = pygame.Rect(0, 0, 30, 16)
    body.midbottom = (bx, by - 2)
    for wx in (body.x + 5, body.right - 5):
        pygame.draw.circle(surface, (20, 20, 24), (wx, body.bottom), 4)
    pygame.draw.rect(surface, shade(color, 0.6), body.move(0, 2), border_radius=5)
    pygame.draw.rect(surface, color, body, border_radius=5)
    roof = pygame.Rect(0, 0, 18, 10)
    roof.midbottom = (bx, body.top + 4)
    pygame.draw.rect(surface, shade(color, 0.85), roof, border_radius=4)
    pygame.draw.rect(surface, (120, 170, 210), roof.inflate(-4, -4), border_radius=3)
    pygame.draw.line(surface, (220, 240, 255), (roof.x + 3, roof.y + 3), (roof.x + 7, roof.y + 3))
    pygame.draw.rect(surface, (255, 240, 170), (body.x + 1, body.bottom - 6, 4, 3))
    pygame.draw.rect(surface, (255, 240, 170), (body.right - 5, body.bottom - 6, 4, 3))
    pygame.draw.line(surface, shade(color, 1.35), (body.x + 4, body.y + 2), (body.right - 4, body.y + 2))


def draw_palm(surface: pygame.Surface, base: tuple[int, int], seed: int, time_s: float) -> None:
    """Palmera de costa con hojas que se mecen."""
    bx, by = base
    sway = math.sin(time_s * 1.2 + seed) * 2
    draw_shadow(surface, (bx + 8, by - 2), 30, 10, 80)
    top = (bx + 4 + sway, by - 40)
    for i in range(6):
        t0, t1 = i / 6, (i + 1) / 6
        p0 = (bx + (top[0] - bx) * t0, by + (top[1] - by) * t0)
        p1 = (bx + (top[0] - bx) * t1, by + (top[1] - by) * t1)
        pygame.draw.line(surface, (140, 100, 60) if i % 2 else (116, 82, 50), p0, p1, 5)
    for angle in (-160, -120, -60, -20, 30, 150):
        rad = math.radians(angle + sway * 3)
        tip = (top[0] + 18 * math.cos(rad), top[1] + 10 * math.sin(rad) + 6)
        mid = (top[0] + 10 * math.cos(rad), top[1] + 6 * math.sin(rad) - 3)
        pygame.draw.lines(surface, (40, 130, 60), False, [top, mid, tip], 4)
        pygame.draw.lines(surface, (80, 180, 90), False, [top, mid, tip], 1)
    pygame.draw.circle(surface, (110, 74, 40), (round(top[0]), round(top[1] + 2)), 3)
