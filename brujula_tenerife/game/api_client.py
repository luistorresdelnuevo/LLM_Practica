"""Cliente HTTP no bloqueante para ``POST /chat``.

Cada petición se ejecuta en un hilo y deja el resultado en una cola que el
bucle de Pygame consulta en cada fotograma, por lo que el juego nunca se
congela. El cliente no conoce claves, prompts ni embeddings.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

import requests

from .settings import API_TIMEOUT_SECONDS, API_URL, PERSONA


@dataclass
class ChatResult:
    """Resultado ya preparado para mostrarse en el diálogo."""

    request_id: int
    npc_name: str
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    error: str | None = None


Poster = Callable[..., Any]


class ApiClient:
    """Envía preguntas en segundo plano y entrega respuestas por cola."""

    def __init__(self, url: str = API_URL, timeout: float = API_TIMEOUT_SECONDS,
                 poster: Poster = requests.post) -> None:
        self.url = url
        self.timeout = timeout
        self._poster = poster
        self._results: "queue.Queue[ChatResult]" = queue.Queue()
        self._next_id = 0
        self.pending = 0

    def send(self, player_id: str, message: str, scene: str,
             quest: str | None, npc_name: str) -> int:
        """Lanza la petición en un hilo y devuelve su identificador."""
        self._next_id += 1
        request_id = self._next_id
        payload = {
            "player_id": player_id,
            "message": message,
            "game_context": {"scene": scene, "quest": quest, "npc": npc_name[:40],
                             "persona": PERSONA},
        }
        self.pending += 1
        threading.Thread(target=self._worker, args=(request_id, npc_name, payload),
                         daemon=True).start()
        return request_id

    def poll(self) -> ChatResult | None:
        """Devuelve un resultado si ya ha llegado, sin esperar."""
        try:
            result = self._results.get_nowait()
        except queue.Empty:
            return None
        self.pending -= 1
        return result

    def _worker(self, request_id: int, npc_name: str, payload: dict[str, Any]) -> None:
        self._results.put(self._post(request_id, npc_name, payload))

    def _post(self, request_id: int, npc_name: str, payload: dict[str, Any]) -> ChatResult:
        try:
            response = self._poster(self.url, json=payload, timeout=self.timeout)
            data = response.json()
        except requests.ConnectionError:
            return ChatResult(request_id, npc_name, "",
                              error="No hay conexión con el guía. ¿Has iniciado la API? "
                                    "(scripts\\iniciar_api.ps1)")
        except requests.Timeout:
            return ChatResult(request_id, npc_name, "",
                              error="El guía tarda demasiado en responder. Inténtalo otra vez.")
        except (requests.RequestException, ValueError):
            return ChatResult(request_id, npc_name, "",
                              error="La respuesta de la API no es válida.")

        return ChatResult(
            request_id=request_id,
            npc_name=npc_name,
            answer=str(data.get("answer", "")),
            citations=list(data.get("citations") or []),
            tools_used=list(data.get("tools_used") or []),
            error=data.get("error"),
        )
