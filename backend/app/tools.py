import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from fastmcp import Client

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:3333/mcp")

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache" / "wiki"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

WIKI_BASE = "https://fr.wikipedia.org"
USER_AGENT = "StreamtechBot/1.0 (local test; contact: local@example.com)"


class MCPToolClient:
    def __init__(self, mcp_url: str | None = None):
        self._mcp_url = mcp_url or MCP_URL
        self._client = Client(self._mcp_url)

    async def call_tool(self, name: str, kwargs: dict):
        async with self._client:
            return await self._client.call_tool(name, kwargs)


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip().lower())
    return cleaned.strip("_") or "unknown"


def _clean_text(text: str) -> str:
    text = re.sub(r"\[[0-9]+\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_summary(soup: BeautifulSoup) -> str:
    container = soup.select_one("div.mw-parser-output")
    if not container:
        return ""

    sentences = []
    for p in container.find_all("p", recursive=False):
        raw = _clean_text(p.get_text(" ", strip=True))
        if not raw:
            continue
        parts = re.split(r"(?<=[.!?])\s+", raw)
        for part in parts:
            if part:
                sentences.append(part)
            if len(sentences) >= 4:
                break
        if len(sentences) >= 4 or sum(len(s) for s in sentences) >= 800:
            break

    summary = " ".join(sentences[:4]).strip()
    return summary[:800]


def _extract_infobox(soup: BeautifulSoup) -> dict:
    infobox = {}
    table = soup.select_one("table.infobox, table.infobox_v2")
    if table:
        for row in table.find_all("tr"):
            header = row.find("th")
            value = row.find("td")
            if not header or not value:
                continue
            key = _clean_text(header.get_text(" ", strip=True))
            val = _clean_text(value.get_text(" ", strip=True))
            if key and val:
                infobox[key] = val
        return infobox

    box = soup.select_one("div.infobox")
    if not box:
        return infobox

    for row in box.select("div.infobox__row"):
        label = row.select_one("div.infobox__label")
        value = row.select_one("div.infobox__value, div.infobox__data")
        if label and value:
            key = _clean_text(label.get_text(" ", strip=True))
            val = _clean_text(value.get_text(" ", strip=True))
            if key and val:
                infobox[key] = val

    if infobox:
        return infobox

    for dt, dd in zip(box.find_all("dt"), box.find_all("dd")):
        key = _clean_text(dt.get_text(" ", strip=True))
        val = _clean_text(dd.get_text(" ", strip=True))
        if key and val:
            infobox[key] = val

    if infobox:
        return infobox

    for row in box.find_all("tr"):
        header = row.find("th")
        value = row.find("td")
        if not header or not value:
            continue
        key = _clean_text(header.get_text(" ", strip=True))
        val = _clean_text(value.get_text(" ", strip=True))
        if key and val:
            infobox[key] = val

    return infobox


def _filter_infobox(infobox: dict) -> dict:
    priority = {}
    for key, value in infobox.items():
        lowered = key.lower()
        if "réalisation" in lowered or "réalisateur" in lowered:
            priority[key] = value
        elif "date de sortie" in lowered or "sortie" in lowered:
            priority[key] = value
        elif "durée" in lowered:
            priority[key] = value
        elif "pays" in lowered:
            priority[key] = value
        elif "budget" in lowered:
            priority[key] = value
        elif "box-office" in lowered or "box office" in lowered:
            priority[key] = value
        elif "entrées" in lowered or "entrees" in lowered:
            priority[key] = value
    return priority


def _extract_awards(soup: BeautifulSoup) -> str:
    headers = soup.select("span.mw-headline")
    for header in headers:
        title = header.get_text(strip=True).lower()
        if "récompense" in title or "prix" in title:
            section = header.parent
            texts = []
            for sibling in section.find_all_next():
                if sibling.name and sibling.name.startswith("h"):
                    break
                if sibling.name in {"p", "ul", "ol"}:
                    chunk = _clean_text(sibling.get_text(" ", strip=True))
                    if chunk:
                        texts.append(chunk)
                if sum(len(t) for t in texts) >= 600:
                    break
            result = " ".join(texts).strip()
            return result[:600]
    return ""


async def scrape_wikipedia(query: str, refresh: bool = False) -> dict:
    slug = _slugify(query)
    cache_path = CACHE_DIR / f"{slug}.json"
    if cache_path.exists() and not refresh:
        with cache_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    headers = {
        "User-Agent": USER_AGENT,
        "From": "local@example.com",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=10.0, headers=headers
    ) as client:
        direct_slug = query.strip().replace(" ", "_")
        direct_url = f"{WIKI_BASE}/wiki/{direct_slug}"
        page = await client.get(direct_url)
        page_soup = BeautifulSoup(page.text, "html.parser")

        if page.status_code in {403, 429}:
            rest_url = f"{WIKI_BASE}/api/rest_v1/page/html/{quote(direct_slug)}"
            rest_page = await client.get(rest_url)
            if rest_page.status_code == 200:
                page_url = direct_url
                page_soup = BeautifulSoup(rest_page.text, "html.parser")
            else:
                data = {
                    "query": query,
                    "error": f"Accès Wikipédia refusé ({page.status_code}).",
                }
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return data

        if page_soup.select_one(".noarticletext"):
            search = await client.get(f"{WIKI_BASE}/w/index.php", params={"search": query})
            soup = BeautifulSoup(search.text, "html.parser")
            result_link = soup.select_one(".mw-search-result-heading a")
            if result_link:
                page_url = WIKI_BASE + result_link["href"]
                page = await client.get(page_url)
                page_soup = BeautifulSoup(page.text, "html.parser")
            else:
                data = {
                    "query": query,
                    "error": "Page Wikipédia introuvable.",
                }
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return data
        else:
            page_url = str(page.url)

    title_node = page_soup.select_one("#firstHeading")
    title = _clean_text(title_node.get_text(strip=True)) if title_node else query
    summary = _extract_summary(page_soup)
    infobox = _extract_infobox(page_soup)
    infobox_priority = _filter_infobox(infobox)
    awards = _extract_awards(page_soup)

    data = {
        "query": query,
        "wikipedia_url": page_url,
        "title": title,
        "summary": summary,
        "infobox": infobox,
        "infobox_priority": infobox_priority,
        "recompenses": awards,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data
