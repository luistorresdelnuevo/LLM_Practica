"""Pruebas del asistente y del contrato con un cliente OpenAI simulado."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import api
from backend.config import PDF_PATH
from backend.game_adapter import ChatRequest, ChatResponse
from backend.rag import load_pdf_documents, split_documents
from backend.weather import get_weather
from conftest import FIXED_TODAY


def ask(assistant: Any, player: str, message: str, scene: str = "Anaga") -> ChatResponse:
    return assistant.chat(ChatRequest(player_id=player, message=message,
                                      game_context={"scene": scene, "quest": None}))


def test_pdf_chunks_keep_citable_metadata() -> None:
    chunks = split_documents(load_pdf_documents(PDF_PATH))
    assert chunks
    meta = chunks[0].metadata
    assert meta["source_name"] == "TENERIFE.pdf"
    assert meta["chunk_id"].startswith("B-")
    assert "page_label" in meta


def test_tourist_question_uses_rag_with_real_citations(assistant: Any) -> None:
    response = ask(assistant, "p1", "¿Qué playa hay en Anaga?")
    assert response.tools_used == []
    assert response.citations, "debe devolver citas"
    citation = response.citations[0]
    assert citation.chunk_id == "B-0" and citation.page == "10"
    assert citation.source == "TENERIFE.pdf"


def test_unanswerable_question_has_no_citations(assistant: Any) -> None:
    response = ask(assistant, "p1", "¿Cuál es la capital de Japón?")
    assert "No tengo información suficiente" in response.answer
    assert response.citations == []


def test_follow_up_uses_history(assistant: Any) -> None:
    first = ask(assistant, "p1", "¿Qué se visita en Anaga?")
    second = ask(assistant, "p1", "¿Y qué playa hay allí?")
    assert "(con historial)" not in first.answer
    assert "(con historial)" in second.answer


def test_players_do_not_share_history(assistant: Any) -> None:
    ask(assistant, "jugador_a", "¿Qué se visita en Anaga?")
    other = ask(assistant, "jugador_b", "¿Y qué playa hay allí?")
    assert "(con historial)" not in other.answer
    assert other.session_id != ask(assistant, "jugador_a", "hola").session_id


def test_history_is_trimmed(assistant: Any) -> None:
    for i in range(8):
        ask(assistant, "p9", f"pregunta {i} sobre Anaga")
    assert len(assistant.store.recent("partida-p9")) == assistant.store.max_turns


def test_weather_question_uses_get_weather(assistant: Any) -> None:
    response = ask(assistant, "p2", "¿Qué tiempo hará mañana?")
    assert response.tools_used == ["get_weather"]
    assert response.error is None


def test_route_request_uses_recommend_route(assistant: Any) -> None:
    response = ask(assistant, "p3", "Dame una ruta de 3 horas")
    assert response.tools_used == ["recommend_route"]
    assert response.citations, "la ruta conserva las fuentes del RAG"


def test_get_weather_validation() -> None:
    ok = get_weather("2026-10-21", today=FIXED_TODAY)
    assert ok["success"] and ok["simulated"]
    assert ok == get_weather("2026-10-21", today=FIXED_TODAY), "determinista"
    assert not get_weather("21/10/2026", today=FIXED_TODAY)["success"]
    assert not get_weather("2026-10-01", today=FIXED_TODAY)["success"]
    assert not get_weather("2027-10-01", today=FIXED_TODAY)["success"]


def test_backend_failure_returns_controlled_error(assistant: Any) -> None:
    def boom(**_: Any) -> Any:
        raise TimeoutError("sk-secret-should-not-leak")

    assistant.client.responses.create = boom
    response = ask(assistant, "p4", "¿Qué ver en el Teide?")
    assert response.error and "TimeoutError" in response.error
    assert "sk-" not in response.model_dump_json()


def test_request_validation() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(player_id="con espacios", message="hola")
    with pytest.raises(ValidationError):
        ChatRequest(player_id="p1", message="   ")


@pytest.fixture
def http(assistant: Any) -> TestClient:
    api.app.state.assistant = assistant
    with TestClient(api.app) as client:
        yield client
    api.app.state.assistant = None


def test_api_contract(http: TestClient, settings: Any) -> None:
    body = {"player_id": "p5", "message": "¿Qué ver en Santa Cruz?",
            "game_context": {"scene": "Santa Cruz", "quest": "Sellos"}}
    response = http.post("/chat", json=body)
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"answer", "citations", "tools_used", "session_id", "error"}
    assert data["session_id"] == "partida-p5"
    assert settings.openai_api_key not in response.text
    assert http.get("/health").json()["assistant_ready"] is True


def test_api_invalid_request_keeps_contract(http: TestClient) -> None:
    response = http.post("/chat", json={"player_id": "p5"})
    assert response.status_code == 422
    assert set(response.json()) == {"answer", "citations", "tools_used", "session_id", "error"}


def test_noir_persona_changes_tone_not_rules(assistant: Any) -> None:
    from backend.rag import RAG_INSTRUCTIONS

    request = ChatRequest(player_id="noir1", message="¿Qué playa hay en Anaga?",
                          game_context={"scene": "Anaga", "npc": "El Lagarto", "persona": "noir"})
    response = assistant.chat(request)
    rag_call = assistant.client.responses.calls[-1]
    assert rag_call["instructions"].startswith(RAG_INSTRUCTIONS), "las reglas del RAG se mantienen"
    assert "El Lagarto" in rag_call["instructions"] and "[Fuente N]" in rag_call["instructions"]
    assert response.citations, "el tono no elimina las citas"


def test_default_persona_is_neutral(assistant: Any) -> None:
    from backend.rag import RAG_INSTRUCTIONS

    ask(assistant, "neutro", "¿Qué playa hay en Anaga?")
    assert assistant.client.responses.calls[-1]["instructions"] == RAG_INSTRUCTIONS
    with pytest.raises(ValidationError):
        ChatRequest(player_id="p", message="hola", game_context={"persona": "pirata"})
