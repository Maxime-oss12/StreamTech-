# StreamTech

Projet IA local (Ollama) + outils cinema (TMDB/Wikipedia) avec un front web.

## Dossiers
- `backend/` : API FastAPI + orchestrator + MCP + scraping
- `frontend/` : interface web (HTML/CSS/JS)

## Lancer en local
1) MCP server :
   `python3 backend/mcp_server.py`
2) API :
   `python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
3) Front :
   `python3 -m http.server 5501 --directory frontend`
   puis ouvrir `http://127.0.0.1:5501`
