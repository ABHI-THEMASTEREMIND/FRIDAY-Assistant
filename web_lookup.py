"""Small, spoken-answer web lookup for FRIDAY."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request


USER_AGENT = "FRIDAY-personal-assistant/1.0"


def _request_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def _shorten(text: str, maximum: int = 440) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= maximum:
        return text
    shortened = text[:maximum].rsplit(". ", 1)[0].strip()
    return (shortened or text[:maximum]).rstrip(".,; ") + "."


def _related_text(items: list[dict]) -> str:
    for item in items:
        if "Text" in item and item["Text"]:
            return item["Text"]
        nested = item.get("Topics", [])
        if nested:
            found = _related_text(nested)
            if found:
                return found
    return ""


def spoken_web_answer(query: str) -> str | None:
    """Return a short factual answer, or None when no safe concise result exists."""
    try:
        encoded = urllib.parse.urlencode(
            {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        )
        instant = _request_json(f"https://api.duckduckgo.com/?{encoded}")
        answer = instant.get("AbstractText") or instant.get("Answer") or instant.get("Definition")
        answer = answer or _related_text(instant.get("RelatedTopics", []))
        if answer:
            return _shorten(answer)

        search = _request_json(
            "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": 1,
                    "format": "json",
                }
            )
        )
        results = search.get("query", {}).get("search", [])
        if not results:
            return None
        title = results[0]["title"]
        summary = _request_json(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + urllib.parse.quote(title.replace(" ", "_"))
        )
        return _shorten(summary.get("extract", "")) or None
    except Exception:
        return None
