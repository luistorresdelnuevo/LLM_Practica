"""Historial conversacional separado por sesión.

Reproduce ``conversation_histories`` y ``answer_with_memory`` del notebook:
cada sesión guarda pares pregunta/respuesta y solo se envían al modelo los
últimos ``MAX_HISTORY_TURNS`` turnos. Se añade un ``Lock`` porque FastAPI
atiende peticiones en varios hilos.
"""

from __future__ import annotations

import threading

from .config import MAX_HISTORY_TURNS

Turn = dict[str, str]


class ConversationStore:
    """Historiales en memoria indexados por ``session_id``."""

    def __init__(self, max_turns: int = MAX_HISTORY_TURNS) -> None:
        if max_turns <= 0:
            raise ValueError("max_turns debe ser mayor que cero.")
        self.max_turns = max_turns
        self._histories: dict[str, list[Turn]] = {}
        self._lock = threading.Lock()

    def recent(self, session_id: str) -> list[Turn]:
        """Devuelve una copia de los últimos turnos de la sesión."""
        with self._lock:
            history = self._histories.get(session_id, [])
            return [dict(turn) for turn in history[-self.max_turns:]]

    def append(self, session_id: str, question: str, answer: str) -> None:
        """Guarda un turno con la pregunta original y recorta el historial."""
        with self._lock:
            history = self._histories.setdefault(session_id, [])
            history.append({"question": question, "answer": answer})
            if len(history) > self.max_turns:
                del history[:-self.max_turns]

    def reset(self, session_id: str) -> None:
        """Elimina el historial de una sesión."""
        with self._lock:
            self._histories.pop(session_id, None)


def format_history(history: list[Turn]) -> str:
    """Representación textual del historial usada en el notebook."""
    lines = []
    for turn in history:
        lines.append(f"Usuario: {turn['question']}")
        lines.append(f"Asistente: {turn['answer']}")
    return "\n".join(lines)


def contextualize_question(question: str, history: list[Turn]) -> str:
    """Añade el historial reciente a la pregunta, como en el notebook."""
    history_text = format_history(history)
    if not history_text:
        return question
    return f"""
Historial reciente de esta sesión:
{history_text}

Pregunta actual:
{question}

Responde únicamente a la pregunta actual, teniendo en cuenta
el historial para resolver sus referencias.
""".strip()
