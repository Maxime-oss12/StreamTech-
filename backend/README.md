# Backend StreamTech

## Organisation
- `main.py` : point d'entree FastAPI (app + CORS + routes)
- `app/api/` : endpoints REST et schemas Pydantic
- `app/mcp/` : orchestrator (logique LLM + tools + regles)
- `app/clients/` : client Ollama (LLM local)
- `app/tools.py` : MCP tools + scraping Wikipedia + cache
- `mcp_server.py` : serveur MCP (TMDB, scraping, utilitaires)
- `data/cache/wiki/` : cache local du scraping Wikipedia

## Demarrage (local)
1) Serveur MCP :
   `python3 backend/mcp_server.py`
2) API FastAPI :
   `python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`

## Endpoints
- `POST /api/chat` : chat principal
- `GET /api/scrape/wiki?query=Inception` : scraping wiki (cache)
- `POST /chat` : legacy (compat front si besoin)
