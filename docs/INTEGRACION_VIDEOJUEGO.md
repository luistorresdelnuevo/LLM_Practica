# Diseño de integración con el videojuego

La integración se prepara mediante una API local para que el motor no contenga la clave ni dependa de LangChain/OpenAI/Gemini.

```text
Jugador
  ↓ escribe una pregunta
Videojuego (`game/`)
  ↓ HTTP con player_id y contexto del juego
API local (`api.py`)
  ↓
Asistente (`assistant.py`)
  ├── conversación
  ├── RAG Tenerife
  └── get_weather
```

## Contrato propuesto

### Petición

`POST /chat`

```json
{
  "player_id": "identificador estable de la partida",
  "message": "pregunta escrita por el jugador",
  "game_context": {
    "scene": "zona actual",
    "quest": "misión activa o null"
  }
}
```

### Respuesta

```json
{
  "answer": "respuesta para el diálogo del NPC",
  "citations": [],
  "tools_used": [],
  "session_id": "sesión asociada al jugador",
  "error": null
}
```

Debes concretar y validar este contrato con Pydantic. Los valores anteriores son estructura, no una implementación.

## Reglas de separación

- La clave vive en `.env` del backend, nunca en el juego.
- El juego no conoce embeddings, prompts ni herramientas.
- El backend no dibuja ventanas ni controla el personaje.
- `player_id` separa historiales.
- La petición de red no debe congelar el bucle gráfico.
- El cliente debe mostrar un mensaje útil si la API no responde.

## Orden recomendado

1. Termina el notebook.
2. Extrae el código validado a `src/tenerife_assistant`.
3. Prueba el asistente desde Python.
4. Implementa y prueba `/chat` con un cliente HTTP sencillo.
5. Implementa la escena y el NPC.
6. Conecta el diálogo del juego.
7. Evalúa latencia y fallos con la API apagada.

## Decisión pendiente del alumno

El proyecto deja una carpeta `game/` orientada a `pygame-ce` porque comparte Python y simplifica la demostración. Si eliges Godot o Unity, conserva el contrato HTTP y sustituye únicamente el cliente del juego.
