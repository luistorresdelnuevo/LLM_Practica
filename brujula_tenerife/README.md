# Tenerife Noir · El caso del Faro

Videojuego turístico 2D con vista cenital (Pygame) conectado a un asistente con RAG,
memoria y herramientas a través de una API local (FastAPI).

```text
Jugador → Pygame (game/) → POST /chat → FastAPI (backend/api.py)
        → TourismAssistant
            ├── RAG sobre data/TENERIFE.pdf   (backend/rag.py)
            ├── historial por player_id        (backend/conversation.py)
            ├── get_weather(fecha)             (backend/weather.py)
            └── recommend_route(zona, horas)   (backend/routes.py)
        → ChatResponse → ventana de diálogo
```

El juego no importa OpenAI, no genera embeddings y no lee el PDF. La clave solo vive
en el `.env` de la raíz del proyecto y la usa el backend.

## Requisitos

- El entorno `.venv` de la raíz, creado con `scripts\setup_windows.ps1`.
- El archivo `.env` de la raíz con `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL` y
  `OPENAI_EMBEDDING_MODEL`.
- No se añade ninguna dependencia nueva: todo está en `requirements.txt`.

## Ejecución en Windows (PowerShell)

Desde la carpeta `Entrega Final\Entrega Final`:

```powershell
# Terminal 1: API local en http://127.0.0.1:8077
.\brujula_tenerife\scripts\iniciar_api.ps1

# Terminal 2: videojuego
.\brujula_tenerife\scripts\iniciar_juego.ps1

# O ambos a la vez (abre la API en otra ventana)
.\brujula_tenerife\scripts\iniciar_todo.ps1
```

Si PowerShell bloquea los scripts, ejecútalos así:

```powershell
powershell -ExecutionPolicy Bypass -File .\brujula_tenerife\scripts\iniciar_todo.ps1
```

El primer arranque de la API crea los embeddings del PDF y los guarda en
`brujula_tenerife\cache`. Los siguientes arranques reutilizan esa caché.

## Controles

| Tecla | Acción |
|---|---|
| WASD o flechas | Moverse |
| E | Hablar con un guía cercano |
| Enter | Enviar la pregunta |
| Flecha arriba o abajo | Desplazar una respuesta larga |
| Escape | Cerrar el diálogo |

## Historia: Tenerife Noir · El caso del Faro

Thriller criminal de ficción, inspirado en los juegos de crimen de mundo abierto pero
con personajes, nombres y gráficos originales. Rubén «El Faro», contrabandista del
puerto, aparece sin vida en el muelle de Santa Cruz y desaparece el alijo «Polvo de
Luna». Ari, detective de homicidios, debe resolver el caso.

| Personaje | Zona | Papel |
|---|---|---|
| Insp. Salazar | Los Cristianos | Lleva el caso y recuerda el objetivo. No usa la API. |
| Doña Ceniza | Teide | Informante. Pista 1: el coche con barro volcánico. |
| Toni Grúas | Santa Cruz | Informante. Pista 2: el contenedor firmado. |
| El Lagarto | Anaga | Informante. Pista 3: la libreta de El Faro. |

1. **Introducción:** cinemática con franjas negras. Enter avanza y Escape salta.
2. **Pistas:** cada conversación respondida sin error con un informante da su pista y dinero.
   También sube el nivel de búsqueda.
3. **Capítulos:** al cerrar el diálogo se narra la pista sobre un tablero de corcho con
   fotos e hilo rojo.
4. **Final:** con las tres pistas se revela al culpable, se cierra el caso y la patrulla
   sigue libre.

El texto de la trama está en `game/story.py` y el avance lo decide Python, no el LLM.

**Interfaz:** radar circular de la isla, reloj, dinero, cinco estrellas de búsqueda,
banners de pista conseguida, nombre de zona al entrar y objetivo abajo.

**Mapa:** sigue el contorno de Tenerife, con Teno, Anaga, el Teide con Las Cañadas,
Santa Cruz al pie de Anaga y Los Cristianos en el sur. Añade la autopista del sur por
la costa sureste, la carretera del norte, el desvío al Teide, coches aparcados y palmeras.

## Tono de las respuestas

El campo opcional `game_context.persona` elige el tono:

- **`"guia"`:** es el valor por defecto. Usa exactamente las instrucciones RAG del notebook.
- **`"noir"`:** es el que usa el juego. Añade al final instrucciones de estilo de soplón
  de novela negra, con el nombre del personaje en `game_context.npc`.

El estilo solo cambia el tono. Los datos siguen saliendo del PDF con citas reales y la
frase de falta de información se mantiene. No se mencionan crímenes, personas ni drogas
reales. Para jugar con el tono neutro:

```powershell
$env:BRUJULA_PERSONA = "guia"; .\brujula_tenerife\scripts\iniciar_juego.ps1
```

## Contrato de la API

`POST /chat`

```json
{
  "player_id": "jugador-1a2b3c4d5e",
  "message": "¿Qué playa se recomienda en Anaga?",
  "game_context": {"scene": "Anaga", "quest": "Interroga a El Lagarto (Anaga)", "npc": "El Lagarto", "persona": "noir"}
}
```

Respuesta, siempre con las mismas claves:

```json
{
  "answer": "La playa recomendada es la Playa de Benijo [Fuente 1].",
  "citations": [{"reference": "Fuente 1", "source": "TENERIFE.pdf", "page": "5", "chunk_id": "B-5", "score": 0.61}],
  "tools_used": [],
  "session_id": "partida-jugador-1a2b3c4d5e",
  "error": null
}
```

`GET /health` indica si el asistente está listo.

## Cómo decide el asistente

1. El modelo recibe el historial reciente y las dos herramientas.
2. Si la pregunta es meteorológica llama a `get_weather`. Si pide una ruta llama a
   `recommend_route`. Python valida los argumentos con Pydantic y ejecuta la herramienta.
3. Si no hace falta herramienta, se usa `answer_with_rag` sobre la pregunta
   contextualizada con el historial, igual que `answer_with_memory` en el notebook.
4. Las citas se construyen desde los metadatos de los chunks recuperados. Si la
   respuesta es «No tengo información suficiente en la base documental», no hay citas.

## Pruebas

```powershell
cd .\brujula_tenerife
..\.venv\Scripts\python.exe -m pytest
```

Las pruebas usan un cliente OpenAI simulado y Pygame sin ventana, así que no gastan
tokens. Para una prueba real de extremo a extremo con la API en marcha:

```powershell
..\.venv\Scripts\python.exe scripts\probar_api.py
```

## Relación con el notebook

| Notebook | Módulo |
|---|---|
| Configuración y validación del `.env` | `backend/config.py` |
| Carga del PDF, chunking B (800/200), `embed_texts`, coseno, `retrieve_chunks`, `RAG_INSTRUCTIONS`, `answer_with_rag` | `backend/rag.py` |
| `conversation_histories`, `MAX_HISTORY_TURNS`, `answer_with_memory` | `backend/conversation.py` |
| `route_tool_schema`, `recommend_route`, `route_tool_logs` | `backend/routes.py` |

## Limitaciones

- `get_weather` es una **simulación declarada** y determinista, porque el notebook aún
  no tiene esta herramienta. Solo acepta fechas entre hoy y dentro de 14 días.
- El historial vive en memoria: se pierde al reiniciar la API.
- El `.env` indica `RAG_CHUNK_SIZE=500` y `RAG_CHUNK_OVERLAP=120`, pero el notebook
  selecciona el experimento B (800/200). El backend sigue al notebook.
- Las preguntas turísticas hacen dos llamadas al modelo: una para decidir si hace falta
  herramienta y otra para la respuesta RAG.
