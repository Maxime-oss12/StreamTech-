from fastapi import APIRouter, HTTPException

from backend.app.api.schemas import ChatRequest
from backend.app.clients.ollama_client import OllamaError
from backend.app.mcp.orchestrator import run_chat
from backend.app.tools import scrape_wikipedia

router = APIRouter(prefix="/api")


@router.post("/chat")
async def chat(req: ChatRequest):
    try:
        return {"response": await run_chat(req.prompt)}
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/scrape/wiki")
async def scrape_wiki(query: str, refresh: bool = False):
    try:
        return await scrape_wikipedia(query=query, refresh=refresh)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Erreur lors du scraping Wikipedia.") from exc
