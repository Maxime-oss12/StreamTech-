from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.api.schemas import ChatRequest
from app.clients.ollama_client import OllamaError
from app.mcp.orchestrator import run_chat

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.post("/chat")
async def chat_legacy(req: ChatRequest):
    try:
        return {"response": await run_chat(req.prompt)}
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
