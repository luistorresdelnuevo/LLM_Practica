"""Cinemáticas del caso: franjas de cine, tablero de pistas y subtítulos."""

from __future__ import annotations

import math

import pygame

from .dialogue import wrap_text
from .hud import get_font
from .render import Palette, draw_character, shade
from .settings import HEIGHT, WIDTH
from .story import Page

BAR_HEIGHT = 70

# Fotos del tablero: zona -> (posición relativa, paleta simplificada del sospechoso).
BOARD_PHOTOS: dict[str, tuple[tuple[int, int], Palette]] = {
    "Teide": ((-170, 0), Palette(shirt=(110, 104, 110), pants=(60, 50, 50), skin=(222, 180, 150),
                                 hair=(236, 236, 240), hat=(30, 30, 36), jacket=(70, 60, 64))),
    "Santa Cruz": ((0, -14), Palette(shirt=(250, 140, 30), pants=(40, 60, 110), skin=(236, 196, 160),
                                     hair=(60, 40, 30), hat=(250, 210, 40), sunglasses=True, chain=True)),
    "Anaga": ((170, 0), Palette(shirt=(60, 150, 70), pants=(50, 60, 70), skin=(214, 170, 130),
                                hair=(30, 30, 30), hat=(40, 110, 50), sunglasses=True)),
}


def draw_case_board(surface: pygame.Surface, center: tuple[int, int], clues: set[str],
                    time_s: float) -> None:
    """Tablero de corcho con una foto por informante y el hilo rojo de las pistas."""
    cx, cy = center
    board = pygame.Rect(0, 0, 520, 170)
    board.center = center
    pygame.draw.rect(surface, (60, 36, 18), board.move(0, 5), border_radius=8)
    pygame.draw.rect(surface, (176, 128, 80), board, border_radius=8)
    pygame.draw.rect(surface, (120, 80, 44), board, 6, border_radius=8)
    for i in range(40):
        x = board.x + 12 + (i * 37) % (board.w - 24)
        y = board.y + 12 + (i * 53) % (board.h - 24)
        pygame.draw.circle(surface, (160, 112, 68), (x, y), 2)

    pins: list[tuple[int, int]] = []
    for zone, ((dx, dy), palette) in BOARD_PHOTOS.items():
        photo = pygame.Rect(0, 0, 96, 112)
        photo.center = (cx + dx, cy + dy)
        tilt = -2 if dx < 0 else 2
        pygame.draw.rect(surface, (30, 20, 10), photo.move(tilt + 3, 4))
        pygame.draw.rect(surface, (246, 244, 236), photo)
        picture = pygame.Rect(photo.x + 8, photo.y + 8, photo.w - 16, photo.h - 34)
        found = zone in clues
        pygame.draw.rect(surface, (200, 214, 222) if found else (60, 64, 72), picture)
        clip = surface.get_clip()
        surface.set_clip(picture)
        draw_character(surface, (picture.centerx, picture.bottom + 18), palette, scale=1.8,
                       shadow=False)
        surface.set_clip(clip)
        if not found:
            veil = pygame.Surface(picture.size, pygame.SRCALPHA)
            veil.fill((20, 20, 26, 200))
            surface.blit(veil, picture)
            q = get_font(36).render("?", True, (230, 230, 230))
            surface.blit(q, q.get_rect(center=picture.center))
        label = get_font(13, "arial", True).render(zone.upper(), True, (40, 30, 20))
        surface.blit(label, label.get_rect(midbottom=(photo.centerx, photo.bottom - 6)))
        pin = (photo.centerx, photo.y + 2)
        pygame.draw.circle(surface, (40, 10, 10), (pin[0] + 1, pin[1] + 2), 6)
        pygame.draw.circle(surface, (210, 40, 40), pin, 6)
        pygame.draw.circle(surface, (255, 140, 140), (pin[0] - 2, pin[1] - 2), 2)
        if found:
            pins.append(pin)

    for a, b in zip(pins, pins[1:]):
        sag = 10 + 3 * math.sin(time_s * 2)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + sag)
        pygame.draw.lines(surface, (200, 20, 30), False, [a, mid, b], 3)


class Cutscene:
    """Secuencia de páginas; Enter avanza y Escape salta."""

    def __init__(self, pages: list[Page], clues: set[str]) -> None:
        if not pages:
            raise ValueError("Una escena necesita al menos una página.")
        self.pages = pages
        self.needles = set(clues)
        self.index = 0
        self.finished = False
        self._shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._shade.fill((6, 6, 12, 200))

    def handle_event(self, event: pygame.event.Event) -> None:
        """Avanza o salta la cinemática."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_e):
            self.index += 1
            if self.index >= len(self.pages):
                self.finished = True
        elif event.key == pygame.K_ESCAPE:
            self.finished = True

    def draw(self, surface: pygame.Surface, title_font: pygame.font.Font,
             font: pygame.font.Font, time_s: float) -> None:
        """Dibuja la página actual al estilo cinemático."""
        page = self.pages[min(self.index, len(self.pages) - 1)]
        surface.blit(self._shade, (0, 0))
        draw_case_board(surface, (WIDTH // 2, 210), self.needles, time_s)

        pygame.draw.rect(surface, (0, 0, 0), (0, 0, WIDTH, BAR_HEIGHT))
        pygame.draw.rect(surface, (0, 0, 0), (0, HEIGHT - BAR_HEIGHT, WIDTH, BAR_HEIGHT))

        big = get_font(46)
        title = big.render(page.title, True, (255, 255, 255))
        outline = big.render(page.title, True, (0, 0, 0))
        tpos = title.get_rect(midtop=(WIDTH // 2, 318))
        for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2), (3, 3)):
            surface.blit(outline, tpos.move(ox, oy))
        surface.blit(title, tpos)

        y = 384
        for line in wrap_text(page.text, font, WIDTH - 200):
            shadow = font.render(line, True, (0, 0, 0))
            rendered = font.render(line, True, (250, 226, 120))
            rect = rendered.get_rect(midtop=(WIDTH // 2, y))
            surface.blit(shadow, rect.move(2, 2))
            surface.blit(rendered, rect)
            y += font.get_linesize() + 4

        for i in range(len(self.pages)):
            color = (250, 226, 120) if i == self.index else (90, 90, 90)
            pygame.draw.rect(surface, color, (WIDTH // 2 - len(self.pages) * 14 + i * 28,
                                              HEIGHT - BAR_HEIGHT + 22, 20, 4))
        if int(time_s * 2) % 2 == 0:
            hint = font.render("ENTER  continuar      ESC  saltar", True, (200, 200, 200))
            surface.blit(hint, hint.get_rect(midtop=(WIDTH // 2, HEIGHT - BAR_HEIGHT + 36)))
        tag = get_font(20).render("TENERIFE NOIR", True, shade((250, 226, 120), 0.8))
        surface.blit(tag, (24, 24))
