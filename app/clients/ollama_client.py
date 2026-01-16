import os
import requests


class OllamaError(RuntimeError):
    pass

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


def chat(messages, temperature=0.0) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"].strip()
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise OllamaError("Ollama unavailable or returned an invalid response.") from exc
