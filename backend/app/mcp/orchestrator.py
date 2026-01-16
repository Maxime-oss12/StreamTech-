from backend.app.clients.ollama_client import chat as ollama_chat
from backend.app.tools import MCPToolClient, scrape_wikipedia

mcp_client = MCPToolClient()


SYSTEM_PROMPT = (
    "Tu es un assistant IA pour une plateforme de streaming type Netflix.\n\n"

    "RÔLE :\n"
    "- Aider les utilisateurs à trouver des informations sur des films et séries.\n"
    "- Émettre des recommandations personnalisées.\n"
    "- Aider les utilisateurs à gérer leur compte (changer mot de passe, paramètres, etc.).\n\n"

    "RÈGLES STRICTES :\n"
    "- Si la question nécessite une information factuelle (film, série, date, note, casting, résumé, recommandation), "
    "tu DOIS utiliser un outil MCP.\n"
    "- Format OBLIGATOIRE pour l'appel à un outil :\n"
    "  TOOL:nom_du_tool(param1=value1,param2=value2)\n"
    "- AUCUN texte avant ou après un appel de tool.\n"
    "- Ne mentionne jamais les tools dans tes réponses.\n"
    "- N'invente jamais de données.\n"
    "--Si la question concerne la récupération ou réinitialisation d'un mot de passe,tu DOIS utiliser l'outil retrieve_password().\n"
    "- Si la question concerne le compte utilisateur ou autre chose hors catalogue, réponds directement en texte.\n"
    "- Si la question concerne les films populaires, tu DOIS utiliser l'outil get_top_n_popular_movies().\n"
    "- Si la question concerne les series populaires, tu DOIS utiliser l'outil get_top_n_popular_series().\n"
    "- Si la question concerne les films a venir ou les sorties a venir, tu DOIS utiliser l'outil get_upcoming_movies().\n"
    "- Si la question concerne les séries populaires, tu DOIS utiliser l'outil get_top_n_popular_series().\n"
    "- Si la question concerne le temps d'écran, le moment de regarder un film, ou s'il est approprié de regarder quelque chose maintenant,tu DOIS utiliser l'outil recommend_screen_time().\n\n"

    "Outils disponibles :\n"
    "- GetTime()\n"
    "- recommend_screen_time()\n"
    "- get_top_n_popular_movies(top_n: int = 5)\n"
    "- get_top_n_popular_series(top_n: int = 5)\n"
    "- get_upcoming_movies(top_n: int = 5)\n"
    "- get_top_n_popular_series(top_n: int = 5)\n"
    "- multiply(a: float, b: float)\n"
    "- search_movie(title: str)\n"
    "- get_movie_details(title: str)\n"
    "- get_movie_rating(title: str)\n"
    "- compare_ratings(movie1_title: str, movie1_rating: float, movie2_title: str, movie2_rating: float)\n"
    "- retrieve_password()\n\n"

    "Si aucun outil n'est pertinent, réponds normalement en texte."
)

ALLOWED_TOOLS = {
    "GetTime",
    "multiply",
    "retrieve_password",
    "recommend_screen_time",
    "search_movie",
    "get_movie_details",
    "get_movie_rating",
    "compare_ratings",
    "get_top_n_popular_movies",
    "get_top_n_popular_series",
    "get_upcoming_movies",
    "recommend_movies",
}
REQUIRED_ARGS = {
    "search_movie": {"title"},
    "get_movie_details": {"title"},
    "get_movie_rating": {"title"},
    "compare_ratings": {"movie1_title", "movie1_rating", "movie2_title", "movie2_rating"},
    "recommend_movies": {"genre"},
    "multiply": {"a", "b"},
}


def ask_llm(prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    return ollama_chat(messages, temperature=0.0)


async def call_tool(tool_call: str):
    if "(" in tool_call:
        name, args = tool_call.split("(", 1)
        name = name.strip()
        args = args.rstrip(")")
        kwargs = {}
        for item in args.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                kwargs[k.strip()] = v.strip()
    else:
        name = tool_call.strip()
        kwargs = {}

    return await call_tool_with_kwargs(name, kwargs)


async def call_tool_with_kwargs(name: str, kwargs: dict):
    if name.lower() == "multiply":
        kwargs = {k: float(v) for k, v in kwargs.items()}

    result = await mcp_client.call_tool(name, kwargs)

    if hasattr(result, "data"):
        value = result.data
    elif hasattr(result, "structured_content") and result.structured_content:
        value = result.structured_content
    elif hasattr(result, "content") and result.content:
        value = result.content[0].text
    else:
        value = str(result)

    if name.lower() == "multiply":
        return f"{kwargs['a']} × {kwargs['b']} fait {value}"

    return value


def format_tool_result(user_prompt: str, tool_name: str, tool_result) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un assistant cinéma.\n"
                "Transforme les données fournies en une réponse claire, naturelle "
                "et agréable pour l'utilisateur.\n"
                "Ne mentionne jamais les tools.\n"
                "N'invente rien."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question utilisateur : {user_prompt}\n\n"
                f"Outil utilisé : {tool_name}\n\n"
                f"Données retournées : {tool_result}"
            ),
        },
    ]

    return ollama_chat(messages, temperature=0.4)


def answer_without_tools(user_prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un assistant cinéma.\n"
                "Réponds en texte clair et utile.\n"
                "N'utilise aucun outil, n'en parle jamais et n'invente pas de données factuelles."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    response = ollama_chat(messages, temperature=0.2)
    if response.strip().startswith("TOOL:"):
        return (
            "Je peux vous aider pour votre compte, mais je dois répondre en texte "
            "uniquement. Dites-moi précisément ce que vous voulez faire."
        )
    return response


def contains_tool_mention(text: str) -> bool:
    lowered = text.lower()
    tool_markers = [
        "tool:",
        "gettime",
        "multiply",
        "retrieve_password",
        "recommend_screen_time",
        "search_movie",
        "get_movie_details",
        "get_movie_rating",
        "compare_ratings",
        "get_top_n_popular_movies",
        "recommend_movies",
    ]
    return any(marker in lowered for marker in tool_markers)


def extract_title_from_prompt(user_prompt: str) -> str:
    import re

    quoted = re.findall(r"[\"“”']([^\"“”']+)[\"“”']", user_prompt)
    if quoted:
        return quoted[0].strip()

    patterns = [
        r"(?i)cherche\s+(.+)$",
        r"(?i)film\s+(.+)$",
        r"(?i)(?:du film|le film|de|du|sur|pour)\s+(.+)$",
        r"(?i)parle\s+moi\s+d['’]?\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_prompt)
        if match:
            title = match.group(1).strip()
            return title.rstrip(".!? ")

    return user_prompt.strip().rstrip(".!? ")


def is_catalog_prompt(user_prompt: str) -> bool:
    lowered = user_prompt.lower()
    greetings = {
        "salut",
        "bonjour",
        "hello",
        "hi",
        "coucou",
        "yo",
        "hey",
    }
    if lowered.strip() in greetings:
        return False
    keywords = [
        "note",
        "resume",
        "résumé",
        "date",
        "casting",
        "acteurs",
        "fiche",
        "infos",
        "information",
        "parle moi de",
        "film",
        "serie",
        "série",
        "recommande",
        "recommandation",
        "cherche",
        "recherche",
        "top",
    ]
    if any(key in lowered for key in keywords):
        return True
    # Si l'utilisateur tape seulement un titre (1-3 mots), on considère catalogue.
    words = [w for w in user_prompt.strip().split() if w]
    return 1 <= len(words) <= 3


def is_short_title_prompt(user_prompt: str) -> bool:
    lowered = user_prompt.lower().strip()
    greetings = {
        "salut",
        "bonjour",
        "hello",
        "hi",
        "coucou",
        "yo",
        "hey",
    }
    if lowered in greetings:
        return False
    words = [w for w in user_prompt.strip().split() if w]
    return 1 <= len(words) <= 3


def is_time_prompt(user_prompt: str) -> bool:
    lowered = user_prompt.lower().strip()
    keywords = [
        "heure",
        "time",
        "il est quelle heure",
        "quelle heure",
    ]
    return any(key in lowered for key in keywords)


def is_screen_time_prompt(user_prompt: str) -> bool:
    lowered = user_prompt.lower()
    keywords = [
        "temps d'ecran",
        "temps d’écran",
        "temps d'écran",
        "temps d’ecran",
        "moment de regarder",
        "bon moment",
        "regarder un film",
        "regarder quelque chose",
    ]
    return any(key in lowered for key in keywords)


def is_password_prompt(user_prompt: str) -> bool:
    lowered = user_prompt.lower()
    keywords = [
        "mot de passe",
        "password",
        "reinitialiser",
        "réinitialiser",
        "recuperer",
        "récupérer",
        "perdu mon mot de passe",
        "oublie mon mot de passe",
        "oublié mon mot de passe",
    ]
    return any(key in lowered for key in keywords)


def is_about_prompt(user_prompt: str) -> bool:
    lowered = user_prompt.lower()
    return "parle moi de" in lowered or "parle-moi de" in lowered or "parle moi d'" in lowered or "parle-moi d'" in lowered


def is_upcoming_prompt(user_prompt: str) -> bool:
    lowered = user_prompt.lower()
    keywords = [
        "a venir",
        "à venir",
        "prochain",
        "sortie",
        "upcoming",
    ]
    return any(key in lowered for key in keywords)

def needs_wikipedia(user_prompt: str) -> bool:
    lowered = user_prompt.lower()
    keywords = [
        "budget",
        "box-office",
        "box office",
        "entrées",
        "entrees",
        "récompenses",
        "recompenses",
        "wikipedia",
        "wikimedia",
    ]
    return any(key in lowered for key in keywords)


def infer_tool_from_prompt(user_prompt: str) -> tuple[str, dict]:
    lowered = user_prompt.lower()
    if "recommande" in lowered or "recommandation" in lowered:
        return "recommend_movies", {"genre": user_prompt.strip()}
    if "a venir" in lowered or "à venir" in lowered or "prochain" in lowered or "upcoming" in lowered:
        top_n = 5
        for token in lowered.split():
            if token.isdigit():
                top_n = int(token)
                break
        return "get_upcoming_movies", {"top_n": top_n}
    if "top" in lowered and "popul" in lowered and ("serie" in lowered or "série" in lowered):
        top_n = 5
        for token in lowered.split():
            if token.isdigit():
                top_n = int(token)
                break
        return "get_top_n_popular_series", {"top_n": top_n}
    if "top" in lowered and "popul" in lowered:
        top_n = 5
        for token in lowered.split():
            if token.isdigit():
                top_n = int(token)
                break
        return "get_top_n_popular_movies", {"top_n": top_n}
    if "cherche" in lowered or "recherche" in lowered or "top" in lowered:
        return "search_movie", {"title": extract_title_from_prompt(user_prompt)}
    return "get_movie_details", {"title": extract_title_from_prompt(user_prompt)}


async def run_chat(prompt: str) -> str:
    if is_short_title_prompt(prompt):
        try:
            title = extract_title_from_prompt(prompt)
            raw_result = await call_tool_with_kwargs("get_movie_details", {"title": title})
            return raw_result
        except Exception:
            return (
                "Je n'ai pas pu appeler l'outil demandé. "
                "Vérifiez votre requête ou réessayez."
            )
    if is_time_prompt(prompt):
        try:
            raw_result = await call_tool_with_kwargs("GetTime", {})
            try:
                from datetime import datetime

                dt = datetime.strptime(raw_result, "%Y-%m-%d %H:%M:%S")
                return f"Il est {dt.strftime('%Hh%M')}."
            except Exception:
                return f"Il est {raw_result}."
        except Exception:
            return "Je n'ai pas pu recuperer l'heure pour le moment."
    if is_screen_time_prompt(prompt):
        try:
            raw_result = await call_tool_with_kwargs("recommend_screen_time", {})
            return format_tool_result(
                user_prompt=prompt,
                tool_name="recommend_screen_time()",
                tool_result=raw_result,
            )
        except Exception:
            return "Je n'ai pas pu recuperer une recommandation pour le moment."
    if is_password_prompt(prompt):
        try:
            raw_result = await call_tool_with_kwargs("retrieve_password", {})
            return format_tool_result(
                user_prompt=prompt,
                tool_name="retrieve_password()",
                tool_result=raw_result,
            )
        except Exception:
            return "Je n'ai pas pu recuperer la procedure pour le moment."
    if is_upcoming_prompt(prompt):
        try:
            top_n = 5
            for token in prompt.split():
                if token.isdigit():
                    top_n = int(token)
                    break
            raw_result = await call_tool_with_kwargs("get_upcoming_movies", {"top_n": top_n})
            return raw_result
        except Exception:
            return (
                "Je n'ai pas pu appeler l'outil demandé. "
                "Vérifiez votre requête ou réessayez."
            )
    if is_about_prompt(prompt):
        try:
            title = extract_title_from_prompt(prompt)
            raw_result = await call_tool_with_kwargs("get_movie_details", {"title": title})
            return raw_result
        except Exception:
            return (
                "Je n'ai pas pu appeler l'outil demandé. "
                "Vérifiez votre requête ou réessayez."
            )
    if is_catalog_prompt(prompt):
        tool_name, kwargs = infer_tool_from_prompt(prompt)
        try:
            raw_result = await call_tool_with_kwargs(tool_name, kwargs)
            wiki_result = None
            if needs_wikipedia(prompt):
                wiki_result = await scrape_wikipedia(kwargs.get("title") or prompt)
            tool_payload = raw_result
            if wiki_result:
                tool_payload = {"tmdb": raw_result, "wikipedia": wiki_result}
            return format_tool_result(
                user_prompt=prompt,
                tool_name=f"{tool_name}({', '.join(f'{k}={v}' for k, v in kwargs.items())})",
                tool_result=tool_payload,
            )
        except Exception:
            return (
                "Je n'ai pas pu appeler l'outil demandé. "
                "Vérifiez votre requête ou réessayez."
            )
    answer = ask_llm(prompt)
    if "TOOL:" not in answer and contains_tool_mention(answer):
        return answer_without_tools(prompt)

    if "TOOL:" in answer:
        tool_call = answer.split("TOOL:", 1)[1].strip()
        tool_name = tool_call.split("(", 1)[0].strip()
        if tool_name not in ALLOWED_TOOLS:
            return answer_without_tools(prompt)
        kwargs = {}
        if "(" in tool_call:
            _, args = tool_call.split("(", 1)
            args = args.rstrip(")")
            for item in args.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    kwargs[k.strip()] = v.strip()
        if tool_name in {"search_movie", "get_movie_details", "get_movie_rating"} and not kwargs.get("title"):
            kwargs["title"] = extract_title_from_prompt(prompt)
        required = REQUIRED_ARGS.get(tool_name, set())
        missing = [key for key in required if key not in kwargs or kwargs[key] == ""]
        if missing:
            return (
                "Il me manque des informations pour appeler l'outil. "
                f"Merci de préciser : {', '.join(missing)}."
            )
        try:
            raw_result = await call_tool_with_kwargs(tool_name, kwargs)
        except Exception:
            return (
                "Je n'ai pas pu appeler l'outil demandé. "
                "Vérifiez votre requête ou réessayez."
            )
        return format_tool_result(
            user_prompt=prompt,
            tool_name=tool_call,
            tool_result=raw_result,
        )

    return answer
