"""Fixtures compartidas: cliente OpenAI simulado y asistente de prueba."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from langchain_core.documents import Document

BRUJULA_DIR = Path(__file__).resolve().parents[1]
if str(BRUJULA_DIR) not in sys.path:
    sys.path.insert(0, str(BRUJULA_DIR))

from backend.assistant import TourismAssistant  # noqa: E402
from backend.config import INSUFFICIENT_INFO, Settings  # noqa: E402
from backend.rag import RAG_INSTRUCTIONS, RagIndex  # noqa: E402

VOCAB = ["anaga", "teide", "santa", "cruz", "playa", "sendero", "volcán", "puerto"]
FIXED_TODAY = date(2026, 10, 20)


def fake_vector(text: str) -> list[float]:
    """Embedding determinista por recuento de palabras del vocabulario."""
    lowered = text.lower()
    return [float(lowered.count(word)) + 0.01 for word in VOCAB]


class FakeEmbeddings:
    def create(self, model: str, input: list[str]) -> Any:  # noqa: A002
        return SimpleNamespace(data=[SimpleNamespace(embedding=fake_vector(t)) for t in input])


class FakeResponses:
    """Imita ``client.responses.create`` para el router y el RAG."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if kwargs["instructions"].startswith(RAG_INSTRUCTIONS):
            return self._rag_answer(kwargs["input"])
        return self._router(kwargs["input"])

    @staticmethod
    def _text(text: str) -> Any:
        return SimpleNamespace(output=[SimpleNamespace(type="message")], output_text=text, id="resp")

    def _rag_answer(self, prompt: str) -> Any:
        if "japón" in prompt.lower():
            return self._text(INSUFFICIENT_INFO)
        marker = " (con historial)" if "Historial reciente" in prompt else ""
        return self._text(f"Respuesta de la guía{marker} [Fuente 1].")

    def _router(self, conversation: list[Any]) -> Any:
        outputs = [i for i in conversation if isinstance(i, dict) and i.get("type") == "function_call_output"]
        if outputs:
            data = json.loads(outputs[-1]["output"])
            return self._text("Resultado: " + data.get("recommendation", data.get("condicion", "error")))
        last = conversation[-1]["content"].lower()
        if "tiempo" in last:
            call = SimpleNamespace(type="function_call", name="get_weather",
                                   arguments=json.dumps({"fecha": "2026-10-21"}), call_id="c1")
            return SimpleNamespace(output=[call], output_text="", id="r")
        if "ruta" in last:
            call = SimpleNamespace(type="function_call", name="recommend_route",
                                   arguments=json.dumps({"zona": "Anaga", "duracion_horas": 3}), call_id="c2")
            return SimpleNamespace(output=[call], output_text="", id="r")
        return self._text("RAG")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        generation_model="fake-chat",
        embedding_model="fake-emb",
        temperature=0.2,
        top_p=1.0,
        max_output_tokens=250,
        top_k=2,
        api_host="127.0.0.1",
        api_port=8077,
        openai_api_key="sk-test-no-real-key-000",
    )


@pytest.fixture
def fake_client() -> Any:
    return SimpleNamespace(embeddings=FakeEmbeddings(), responses=FakeResponses())


@pytest.fixture
def rag(fake_client: Any, settings: Settings) -> RagIndex:
    texts = [
        "Anaga: sendero de laurisilva y playa de Benijo.",
        "El Teide es un volcán y parque nacional.",
        "Santa Cruz tiene puerto y la plaza de España.",
    ]
    splits = [
        Document(page_content=t, metadata={"chunk_id": f"B-{i}", "source_name": "TENERIFE.pdf",
                                           "page_label": str(10 + i)})
        for i, t in enumerate(texts)
    ]
    embeddings = np.array([fake_vector(t) for t in texts], dtype=np.float32)
    return RagIndex(fake_client, settings, splits, embeddings)


@pytest.fixture
def assistant(fake_client: Any, settings: Settings, rag: RagIndex) -> TourismAssistant:
    return TourismAssistant(fake_client, settings, rag, today_provider=lambda: FIXED_TODAY)
