"""
ai_service.py

Single abstraction over OpenRouter (OpenAI-compatible API).
All backend services call complete_json() and embed() through here.
Changing model or provider touches this file only.
"""
import json
import os
import time
import httpx
from typing import Any

_BASE_URL = "https://openrouter.ai/api/v1"
_TIMEOUT = 90  # seconds — generation can be slow


def _client() -> httpx.Client:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    return httpx.Client(
        base_url=_BASE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("PUBLIC_APP_URL", "http://localhost:3000"),
            "X-Title": "LaBeans",
        },
        timeout=_TIMEOUT,
    )


def _post(path: str, payload: dict) -> httpx.Response:
    """
    POST to the provider. Every failure mode (bad key, DNS, timeout, dropped
    connection) is raised as ValueError, so callers have one exception to handle.
    """
    try:
        with _client() as client:
            return client.post(path, json=payload)
    except httpx.HTTPError as exc:
        raise ValueError(f"Could not reach the AI provider: {type(exc).__name__}: {exc}") from exc


def complete_json(
    messages: list[dict],
    schema: dict,
    model: str | None = None,
    temperature: float = 0.3,
) -> tuple[dict, int]:
    """
    Call the LLM and return (parsed_dict, latency_ms).

    Sends a JSON-schema response_format so the model is constrained.
    Falls back to parsing the raw content if the provider ignores the format.
    Raises ValueError on unparseable output.
    """
    chosen_model = model or os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    payload: dict[str, Any] = {
        "model": chosen_model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "labeans_output",
                "strict": True,
                "schema": schema,
            },
        },
    }

    start = time.monotonic()
    resp = _post("/chat/completions", payload)
    latency_ms = int((time.monotonic() - start) * 1000)

    if resp.status_code != 200:
        raise ValueError(
            f"OpenRouter returned {resp.status_code}: {resp.text[:300]}"
        )

    try:
        raw_content: str = resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Unexpected response shape from OpenRouter: {resp.text[:300]}") from exc

    # Some providers wrap JSON in markdown code fences — strip them
    stripped = raw_content.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("```")[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()

    try:
        return json.loads(stripped), latency_ms
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model output was not valid JSON: {exc}\n{raw_content[:400]}") from exc


def embed(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings via OpenRouter (or a dedicated embeddings endpoint).
    Returns a list of float vectors in the same order as inputs.
    Raises ValueError on failure.
    """
    embed_model = os.environ.get(
        "OPENROUTER_EMBED_MODEL", "openai/text-embedding-3-small"
    )

    payload = {"model": embed_model, "input": texts}

    resp = _post("/embeddings", payload)

    if resp.status_code != 200:
        raise ValueError(
            f"Embeddings endpoint returned {resp.status_code}: {resp.text[:300]}"
        )

    try:
        # Sort by index to preserve order
        items = sorted(resp.json()["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"Unexpected embeddings response: {resp.text[:300]}") from exc
