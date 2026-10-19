"""Local AI connection for FRIDAY using Ollama.

Ollama runs on this computer, so questions do not need a paid cloud API.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")


class LocalAIUnavailable(RuntimeError):
    """Raised when the local Ollama service is unavailable."""


def ask_local_ai(question: str) -> str:
    """Return a concise answer from FRIDAY's local model."""
    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.35, "num_predict": 120},
        "format": {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are FRIDAY, a friendly personal Windows voice assistant. "
                    "Understand natural phrasing. Answer immediately and keep spoken replies "
                    "to one or two short sentences. Never claim you completed an action you "
                    "cannot do. Respond only as JSON matching the requested answer field."
                ),
            },
            # Qwen understands this instruction even on Ollama versions that
            # do not yet honor the API-level `think: false` option.
            {"role": "user", "content": f"/no_think\n{question}"},
        ],
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
        raw_answer = result.get("message", {}).get("content", "").strip()
        # Accept only the structured final answer. This intentionally discards
        # reasoning text even if an older Qwen/Ollama version emits it.
        json_start = raw_answer.find("{")
        if json_start < 0:
            raise LocalAIUnavailable("The local AI did not return a final answer.")
        answer = json.JSONDecoder().raw_decode(raw_answer[json_start:])[0].get("answer", "").strip()
        if not answer:
            raise LocalAIUnavailable("The local AI returned no answer.")
        return answer
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise LocalAIUnavailable(str(error)) from error


def route_spoken_intent(command: str) -> str | None:
    """Map a natural-language request to a safe built-in FRIDAY command.

    This is only used after the fast keyword commands do not match.
    """
    payload = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_predict": 50},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You convert a user's request into ONE permitted FRIDAY command. "
                    "Reply with exactly one of these forms and nothing else: "
                    "OPEN: <chrome|youtube|google|calculator|notepad|settings|files|downloads|documents|camera|spotify>; "
                    "SEARCH: <query>; PLAY: <song>; TIME; DATE; PAUSE; NEXT; PREVIOUS; JOKE; HELP; NONE. "
                    "Use NONE for questions, emails, sensitive actions, or anything not listed."
                ),
            },
            {"role": "user", "content": f"/no_think\n{command}"},
        ],
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        raw = result.get("message", {}).get("content", "").strip().upper()
        raw = re.sub(r"<THINK>.*?</THINK>", "", raw, flags=re.DOTALL).strip()
        match = re.search(
            r"\b(OPEN:\s*(?:CHROME|YOUTUBE|GOOGLE|CALCULATOR|NOTEPAD|SETTINGS|FILES|DOWNLOADS|DOCUMENTS|CAMERA|SPOTIFY)|"
            r"SEARCH:\s*.+|PLAY:\s*.+|TIME|DATE|PAUSE|NEXT|PREVIOUS|JOKE|HELP|NONE)\b",
            raw,
        )
        return match.group(1).strip() if match else None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
