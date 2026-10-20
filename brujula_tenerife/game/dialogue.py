"""Ventana de diálogo con campo de texto, respuesta, fuentes y herramientas."""

from __future__ import annotations

from enum import Enum

import pygame

from .api_client import ChatResult
from .npc import NPC
from .render import vertical_gradient
from .settings import COLORS, HEIGHT, WIDTH

MAX_INPUT_CHARS = 300
WAITING_TEXT = "Consultando al informante..."


class DialogueState(Enum):
    """Fases de una conversación."""

    TYPING = "typing"
    WAITING = "waiting"
    ANSWERED = "answered"
    ERROR = "error"
    STORY = "story"


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Parte el texto en líneas que caben en ``max_width`` píxeles."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        lines.append(current)
    return lines


def _rounded_gradient(size: tuple[int, int], top: tuple[int, int, int],
                      bottom: tuple[int, int, int], radius: int) -> pygame.Surface:
    """Degradado vertical recortado con esquinas redondeadas."""
    surf = vertical_gradient(size, top, bottom)
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return surf


def format_citations(citations: list[dict]) -> str:
    """Resume las fuentes reales devueltas por la API."""
    if not citations:
        return "Fuentes: ninguna"
    parts = [f"{c.get('source', '?')} p.{c.get('page', '?')} ({c.get('chunk_id', '?')})"
             for c in citations]
    return "Fuentes: " + "; ".join(parts)


class Dialogue:
    """Estado y dibujo del diálogo con un NPC."""

    def __init__(self) -> None:
        self.npc: NPC | None = None
        self.state = DialogueState.TYPING
        self.input_text = ""
        self.body = ""
        self.citations: list[dict] = []
        self.tools: list[str] = []
        self.error: str | None = None
        self.request_id: int | None = None
        self.scroll = 0
        self.swallow_e = False
        self._panel_bg: pygame.Surface | None = None

    @property
    def is_open(self) -> bool:
        """Hay un diálogo visible."""
        return self.npc is not None

    def open(self, npc: NPC) -> None:
        """Abre el diálogo con el saludo del guía."""
        self.npc = npc
        self.state = DialogueState.TYPING
        self.input_text = ""
        self.body = npc.greeting
        self.citations, self.tools, self.error = [], [], None
        self.request_id = None
        self.scroll = 0
        self.swallow_e = True

    def open_story(self, npc: NPC, text: str) -> None:
        """Abre un diálogo narrativo sin campo de texto (no usa la API)."""
        self.open(npc)
        self.state = DialogueState.STORY
        self.body = text

    def close(self) -> None:
        """Cierra el diálogo; una respuesta tardía se ignorará."""
        self.npc = None
        self.request_id = None

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Procesa teclado; devuelve la pregunta cuando se pulsa Enter."""
        if not self.is_open:
            return None
        if self.state == DialogueState.STORY:
            if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.close()
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                question = self.input_text.strip()
                if question and self.state != DialogueState.WAITING:
                    self.input_text = ""
                    return question
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 1)
            elif event.key == pygame.K_DOWN:
                self.scroll += 1
        elif event.type == pygame.TEXTINPUT and self.state != DialogueState.WAITING:
            if self.swallow_e and event.text in ("e", "E"):
                # La E que abrió el diálogo no debe escribirse en el campo.
                self.swallow_e = False
                return None
            self.swallow_e = False
            self.input_text = (self.input_text + event.text)[:MAX_INPUT_CHARS]
        return None

    def mark_waiting(self, request_id: int, question: str) -> None:
        """Muestra el estado de espera tras enviar la pregunta."""
        self.state = DialogueState.WAITING
        self.request_id = request_id
        self.body = f"Tú: {question}"
        self.citations, self.tools, self.error = [], [], None
        self.scroll = 0

    def apply_result(self, result: ChatResult) -> bool:
        """Muestra la respuesta si corresponde a la petición visible."""
        if not self.is_open or result.request_id != self.request_id:
            return False
        self.error = result.error
        self.state = DialogueState.ERROR if result.error else DialogueState.ANSWERED
        self.body = result.answer or ""
        self.citations = result.citations
        self.tools = result.tools_used
        self.scroll = 0
        return True

    def draw(self, surface: pygame.Surface, font: pygame.font.Font,
             small: pygame.font.Font, time_s: float) -> None:
        """Dibuja el panel inferior."""
        if self.npc is None:
            return
        panel = pygame.Rect(16, HEIGHT - 290, WIDTH - 32, 274)
        if self._panel_bg is None:
            self._panel_bg = _rounded_gradient(panel.size, (28, 28, 32), (6, 6, 8), 16)
        pygame.draw.rect(surface, (8, 10, 24), panel.move(0, 4), border_radius=16)
        surface.blit(self._panel_bg, panel)
        pygame.draw.rect(surface, (250, 226, 120), panel, 3, border_radius=16)
        pygame.draw.rect(surface, (70, 70, 70), panel.inflate(-10, -10), 1, border_radius=12)

        # Pestaña con el nombre del guía, como en las portátiles clásicas.
        title = font.render(f"{self.npc.name}  ·  {self.npc.zone}", True, (255, 255, 255))
        tab = title.get_rect(bottomleft=(panel.x + 24, panel.y + 6)).inflate(26, 12)
        pygame.draw.rect(surface, tuple(max(0, c - 70) for c in self.npc.color), tab.move(0, 3),
                         border_radius=10)
        pygame.draw.rect(surface, self.npc.color, tab, border_radius=10)
        pygame.draw.rect(surface, (255, 236, 170), tab, 2, border_radius=10)
        surface.blit(title, title.get_rect(center=tab.center))

        self.npc.draw_portrait(surface, (panel.x + 66, panel.y + 74), time_s)
        x, y, width = panel.x + 128, panel.y + 18, panel.w - 146

        body_lines = wrap_text(self.body, small, width)
        if self.state == DialogueState.WAITING:
            dots = "." * (1 + int(time_s * 3) % 3)
            body_lines.append(WAITING_TEXT.rstrip(".") + dots)
        if self.error:
            body_lines += wrap_text(f"⚠ {self.error}", small, width)

        footer: list[tuple[str, tuple[int, int, int]]] = []
        if self.state == DialogueState.ANSWERED:
            for line in wrap_text(format_citations(self.citations), small, width)[:2]:
                footer.append((line, COLORS["text_dim"]))
            tools = ", ".join(self.tools) if self.tools else "ninguna (RAG)"
            footer.append((f"Herramientas: {tools}", COLORS["text_dim"]))

        line_h = small.get_linesize()
        visible = max(1, (panel.bottom - 64 - len(footer) * line_h - y) // line_h)
        self.scroll = min(self.scroll, max(0, len(body_lines) - visible))
        for line in body_lines[self.scroll:self.scroll + visible]:
            color = COLORS["error"] if line.startswith("⚠") else COLORS["text"]
            surface.blit(small.render(line, True, color), (x, y))
            y += line_h
        if len(body_lines) > visible:
            more = small.render("↑↓ para desplazar", True, COLORS["accent"])
            surface.blit(more, (panel.right - more.get_width() - 20, panel.y + 16))

        fy = panel.bottom - 60 - len(footer) * line_h
        for text, color in footer:
            surface.blit(small.render(text, True, color), (x, fy))
            fy += line_h

        if self.state == DialogueState.STORY:
            hint = small.render("Enter o Esc: continuar", True, COLORS["accent"])
            surface.blit(hint, hint.get_rect(bottomright=(panel.right - 20, panel.bottom - 18)))
            return

        box = pygame.Rect(x, panel.bottom - 50, width, 30)
        pygame.draw.rect(surface, (10, 14, 32), box.move(0, 2), border_radius=8)
        pygame.draw.rect(surface, (238, 240, 250), box, border_radius=8)
        pygame.draw.rect(surface, (255, 236, 170), box, 2, border_radius=8)
        cursor = "_" if int(time_s * 2) % 2 == 0 and self.state != DialogueState.WAITING else ""
        prompt = "> " + self.input_text + cursor
        rendered = small.render(prompt, True, (30, 34, 60))
        clip = max(0, rendered.get_width() - (box.w - 16))
        surface.blit(rendered, (box.x + 8, box.y + 4), area=pygame.Rect(clip, 0, box.w - 16, 24))
        for i, text in enumerate(("Enter: enviar", "Esc: cerrar")):
            hint = small.render(text, True, COLORS["text_dim"])
            surface.blit(hint, hint.get_rect(midtop=(panel.x + 66, panel.bottom - 64 + i * 22)))
