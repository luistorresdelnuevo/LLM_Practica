# Entrega final — asistente turístico de Tenerife

Este repositorio está preparado como **estructura de trabajo**, no como solución. El código evaluable y las explicaciones del notebook deben ser escritos por el alumno.

## Objetivo del enunciado

Construir un asistente turístico que combine:

- RAG sobre `data/TENERIFE.pdf`.
- Conversación multiturno con control del contexto.
- Una herramienta `get_weather(fecha)` real o simulada.
- Gestión básica de errores y registro de intentos.
- Evaluación reproducible, visualización y análisis crítico.
- Integración posterior con un videojuego mediante una API local.

## Estructura

```text
Entrega Final/
├── data/TENERIFE.pdf
├── notebooks/entrega_final.ipynb
├── src/tenerife_assistant/
│   ├── config.py
│   ├── rag.py
│   ├── conversation.py
│   ├── weather.py
│   ├── assistant.py
│   ├── api.py
│   └── game_adapter.py
├── game/
├── evaluation/
├── tests/
├── docs/
├── logs/
└── artifacts/vector_store/
```

## Preparación en Windows

El script `scripts/setup_windows.ps1` crea `.venv`, instala las dependencias y registra el kernel:

```powershell
.\scripts\setup_windows.ps1
```

Copia la plantilla de entorno y añade tu propia clave:

```powershell
Copy-Item .env.template .env
```

No subas `.env` al repositorio.

## Abrir el notebook

```powershell
.\scripts\iniciar_jupyter.ps1
```

Selecciona el kernel:

```text
Python (Entrega Final LLM)
```

## Orden de trabajo

1. Lee [PLAN_DE_TRABAJO.md](docs/PLAN_DE_TRABAJO.md).
2. Completa el notebook en orden.
3. Ejecuta y evalúa cada bloque antes de modularizarlo.
4. Traslada únicamente el código validado a `src/tenerife_assistant`.
5. Implementa la API local y después conecta el videojuego.
6. Completa el informe con tus resultados reales.

## Importante

Los archivos Python contienen contratos, docstrings y marcadores `TODO`, pero no implementan RAG, memoria, function calling ni el asistente. Esas partes forman la práctica evaluable.

## Videojuego «La brújula de Tenerife»

El videojuego y su backend están en [brujula_tenerife/](brujula_tenerife/README.md). Desde esta carpeta:

```powershell
.\brujula_tenerife\scripts\iniciar_api.ps1     # terminal 1
.\brujula_tenerife\scripts\iniciar_juego.ps1   # terminal 2
.\brujula_tenerife\scripts\iniciar_todo.ps1    # o ambos a la vez
```
