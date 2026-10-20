# Entrega final — asistente turístico de Tenerife


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

## Notebook
Se encuentra el notebook con el desarrollo y las explicaciones del RAG.


## Videojuego «La brújula de Tenerife»

El videojuego y su backend están en [brujula_tenerife/](brujula_tenerife/README.md). Este videojuego, se ha hecho exclusivamente con IA, utilizando como base el RAG desarrollado en el notebook.

Desde esta carpeta:

```powershell
.\brujula_tenerife\scripts\iniciar_api.ps1     # terminal 1
.\brujula_tenerife\scripts\iniciar_juego.ps1   # terminal 2
.\brujula_tenerife\scripts\iniciar_todo.ps1    # o ambos a la vez
```
