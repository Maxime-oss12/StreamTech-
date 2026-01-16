import requests
from fastmcp import FastMCP
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

mcp = FastMCP(name="custom-tools-mcp-server")

API_KEY_TMDB = "65632612bcfadf9d21c403e16c4df96f"
BASE_URL_TMDB = "https://api.themoviedb.org/3"
GENRE_IDS = {
    "action": 28,
    "aventure": 12,
    "animation": 16,
    "comedie": 35,
    "comédie": 35,
    "crime": 80,
    "documentaire": 99,
    "drame": 18,
    "fantastique": 14,
    "science-fiction": 878,
    "sf": 878,
    "horreur": 27,
    "thriller": 53,
    "romance": 10749,
    "guerre": 10752,
    "musique": 10402,
    "mystere": 9648,
    "mystère": 9648,
    "familial": 10751,
    "historique": 36,
    "western": 37,
    "telefilm": 10770,
    "téléfilm": 10770,
}

# ----------------- OUTILS TEST -----------------
@mcp.tool()
def GetTime() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@mcp.tool()
def multiply(a: float, b: float) -> float:
    return a * b


@mcp.tool()
def read_csv_stats(path: str) -> str:
    df = pd.read_csv(path)
    return df.describe().to_string()


@mcp.tool()
def retrieve_password() -> str:
    """
    Explique la procédure pour réinitialiser le mot de passe Streamtech.
    Réponse finale prête à être affichée à l'utilisateur.
    """
    return (
        "Pour réinitialiser votre mot de passe Streamtech, vous pouvez suivre les étapes suivantes :\n\n"
        "1. Allez sur le site web de Streamtech.\n"
        "2. Cliquez sur l’onglet « Mon compte » en haut à droite de la page.\n"
        "3. Sélectionnez « Mot de passe oublié ».\n"
        "4. Entrez votre adresse e-mail associée à votre compte Streamtech.\n"
        "5. Cliquez sur « Réinitialiser le mot de passe » pour recevoir un e-mail de réinitialisation.\n"
        "6. Suivez les instructions contenues dans l’e-mail pour définir un nouveau mot de passe.\n\n"
        "Si vous rencontrez des difficultés, vous pouvez contacter l’équipe de support client Streamtech pour obtenir de l’aide."
    )


@mcp.tool()
def recommend_screen_time() -> str:
    """
    Recommande un temps d'écran en fonction de l'heure actuelle.
    """
    now = datetime.now()
    hour = now.hour

    if 8 <= hour < 20:
        recommendation = (
            "📱 Temps d'écran recommandé : 1 heure.\n"
            "Profitez d'un film ou d'une série, puis pensez à faire une pause."
        )
    elif 20 <= hour < 24:
        recommendation = (
            "🌙 Temps d'écran recommandé : 2 heures.\n"
            "C'est le moment idéal pour regarder un bon film avant de dormir."
        )
    else:
        recommendation = (
            "😴 Il est tard.\n"
            "Nous vous recommandons d'aller dormir et de reprendre le streaming plus tard."
        )

    return (
        f"🕒 Heure actuelle : {now.strftime('%H:%M')}\n\n"
        f"{recommendation}"
    )



# ----------------- NOUVEAUX OUTILS CINÉ -----------------
@mcp.tool()
def search_movie(title: str, top_n: int = 3) -> str:
    """
    Recherche un film sur TMDB par titre et retourne les top_n résultats
    sous forme de texte structuré.
    """
    url = f"{BASE_URL_TMDB}/search/movie"
    params = {
        "api_key": API_KEY_TMDB,
        "query": title,
        "language": "fr-FR",
        "include_adult": False
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()["results"]

    # Filtrer films avec résumé
    data = [m for m in data if m.get("overview")]

    # Trier par note moyenne décroissante
    data.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

    if not data:
        return "Aucun film trouvé."

    result_str = ""
    for movie in data[:top_n]:
        result_str += (
            f"Titre: {movie['title']}\n"
            f"Date de sortie: {movie.get('release_date', 'N/A')}\n"
            f"Note: {movie.get('vote_average', 'N/A')}\n"
            f"Résumé: {movie.get('overview', 'N/A')}\n"
            "----------------------------------------\n"
        )
    return result_str


@mcp.tool()
def get_movie_details(title: str) -> str:
    """
    Récupère les détails du film le plus pertinent correspondant au titre.
    """
    url = f"{BASE_URL_TMDB}/search/movie"
    params = {
        "api_key": API_KEY_TMDB,
        "query": title,
        "language": "fr-FR",
        "include_adult": False
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()["results"]

    if not data:
        return "Aucun film trouvé."

    normalized = title.strip().lower()

    def score(movie):
        title_match = 1 if movie.get("title", "").strip().lower() == normalized else 0
        lang = movie.get("original_language", "")
        lang_bonus = 1 if lang in {"en", "fr"} else 0
        has_date = 1 if movie.get("release_date") else 0
        return (
            title_match * 100,
            lang_bonus * 10,
            has_date * 5,
            movie.get("vote_count", 0),
            movie.get("popularity", 0),
            movie.get("vote_average", 0),
        )

    movie = max(data, key=score)

    return (
        f"Titre: {movie['title']}\n"
        f"Date de sortie: {movie.get('release_date', 'N/A')}\n"
        f"Note: {movie.get('vote_average', 'N/A')}\n"
        f"Résumé: {movie.get('overview', 'N/A')}\n"
        f"Langue originale: {movie.get('original_language', 'N/A')}\n"
        f"Popularité: {movie.get('popularity', 'N/A')}\n"
    )


@mcp.tool()
def get_movie_rating(title: str) -> float:
    """
    Récupère la note TMDB du film le plus pertinent correspondant au titre.
    Retourne uniquement la note (float).
    """
    url = f"{BASE_URL_TMDB}/search/movie"
    params = {
        "api_key": API_KEY_TMDB,
        "query": title,
        "language": "fr-FR",
        "include_adult": False
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    results = response.json().get("results", [])

    if not results:
        raise ValueError(f"Aucun film trouvé pour : {title}")

    movie = max(
        results,
        key=lambda x: (x.get("vote_average", 0), x.get("vote_count", 0))
    )

    return float(movie.get("vote_average", 0.0))


@mcp.tool()
def get_top_movies_by_genre(genre_name: str, top_n: int = 5, language: str = "fr-FR") -> str:
    """
    Renvoie les top N films par genre via TMDB.
    genre_name : nom du genre (ex: action, drame, comedie)
    """
    genre_key = genre_name.strip().lower()
    genre_id = GENRE_IDS.get(genre_key)
    if genre_id is None:
        return (
            "Genre non reconnu. Exemples: action, drame, comedie, science-fiction, "
            "thriller, romance, horreur."
        )

    url = f"{BASE_URL_TMDB}/discover/movie"
    params = {
        "api_key": API_KEY_TMDB,
        "with_genres": genre_id,
        "language": language,
        "sort_by": "vote_average.desc",
        "vote_count.gte": 200,
        "include_adult": False,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    results = response.json().get("results", [])

    if not results:
        return "Aucun film trouvé pour ce genre."

    top_n = min(top_n, len(results))
    result_str = f"🎬 Top {top_n} films ({genre_name}) :\n\n"
    for movie in results[:top_n]:
        result_str += (
            f"Titre: {movie.get('title', 'N/A')}\n"
            f"Date de sortie: {movie.get('release_date', 'N/A')}\n"
            f"Note: {movie.get('vote_average', 'N/A')}\n"
            "----------------------------------------\n"
        )

    return result_str


@mcp.tool()
def compare_ratings(
    movie1_title: str,
    movie1_rating: float,
    movie2_title: str,
    movie2_rating: float
) -> str:
    """
    Compare deux notes de films et indique lequel est le mieux noté.
    """
    if movie1_rating > movie2_rating:
        best = movie1_title
    elif movie2_rating > movie1_rating:
        best = movie2_title
    else:
        best = "Égalité parfaite 🎬"

    return (
        f"🎥 {movie1_title} : ⭐ {movie1_rating}\n"
        f"🎥 {movie2_title} : ⭐ {movie2_rating}\n\n"
        f"🏆 Film le mieux noté : {best}"
    )


@mcp.tool()
def get_top_n_popular_movies(top_n: int = 5) -> str:
    """
    Renvoie les top N films populaires depuis TMDB via scraping.
    """
    url = "https://www.themoviedb.org/movie"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return f"Impossible d'accéder à TMDB (status {response.status_code})"

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select("div.card.style_1")

    if not cards:
        return "Aucun film trouvé sur la page Populaires."

    top_n = min(top_n, len(cards))

    result_str = f"🎬 Top {top_n} films Populaires sur TMDB:\n\n"
    for card in cards[:top_n]:
        title_tag = card.select_one("h2 a")
        title = title_tag.text.strip() if title_tag else "N/A"

        year_tag = card.select_one("span.release_date")
        year = year_tag.text.strip() if year_tag else "N/A"

        rating_tag = card.select_one("div.user_score_chart")
        rating = rating_tag.get("data-percent") if rating_tag else "N/A"

        overview_tag = card.select_one("p.overview")
        overview = overview_tag.text.strip() if overview_tag else "N/A"

        result_str += (
            f"Titre: {title}\n"
            f"Année: {year}\n"
            f"Note TMDB: {rating}/100\n"
            f"Résumé: {overview}\n"
            "----------------------------------------\n"
        )

    return result_str


@mcp.tool()
def get_top_n_popular_series(top_n: int = 5) -> str:
    """
    Récupère les top N séries "Populaires" depuis la page TMDB via scraping.
    top_n : nombre de séries à récupérer
    """
    url = "https://www.themoviedb.org/tv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return f"Impossible d'accéder à TMDB (status {response.status_code})"

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select("div.card.style_1")

    if not cards:
        return "Aucune série trouvée sur la page Populaires."

    top_n = min(top_n, len(cards))

    result_str = f"📺 Top {top_n} séries Populaires sur TMDB:\n\n"
    for card in cards[:top_n]:
        title_tag = card.select_one("h2 a")
        title = title_tag.text.strip() if title_tag else "N/A"

        rating_tag = card.select_one("div.user_score_chart")
        rating = rating_tag.get("data-percent") if rating_tag else "N/A"

        result_str += (
            f"Titre: {title}\n"
            f"Note TMDB: {rating}/100\n"
            "----------------------------------------\n"
        )

    return result_str


@mcp.tool()
def get_upcoming_movies(top_n: int = 5) -> str:
    """
    Récupère les films à venir via l'API TMDB.
    Trié par date de sortie croissante.
    """
    url = f"{BASE_URL_TMDB}/movie/upcoming"
    params = {
        "api_key": API_KEY_TMDB,
        "language": "fr-FR",
        "page": 1,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    results = response.json().get("results", [])

    target_year = "2026"
    results = [
        movie for movie in results
        if movie.get("release_date", "").startswith(target_year)
    ]

    if not results:
        return f"Aucun film a venir trouve pour {target_year}."

    if not results:
        return "Aucun film a venir trouve via l'API TMDB."

    def _sort_key(item):
        return item.get("release_date") or "9999-12-31"

    results.sort(key=_sort_key)
    top_n = min(top_n, len(results))

    result_str = f"🎬 Top {top_n} films a venir (tries par date):\n\n"
    for movie in results[:top_n]:
        result_str += (
            f"Titre: {movie.get('title', 'N/A')}\n"
            f"Date de sortie: {movie.get('release_date', 'N/A')}\n"
            f"Note: {movie.get('vote_average', 'N/A')}\n"
            f"Resume: {movie.get('overview', 'N/A')}\n"
            "----------------------------------------\n"
        )

    return result_str

# idée de fonctions futures :
# 1) recommandation d'un film en fonction d'un genre
# 2) récupération des acteurs principaux d'un film
# 3) extraire les recommandations dun film en csv/xlxs

# ----------------- LANCEMENT MCP -----------------
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3333)
