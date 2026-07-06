"""Helpers for extracting JSON from (possibly noisy) LLM responses."""

from __future__ import annotations

import json
from typing import Any

from ..errors import InvalidJSONError


def extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from ``text``.

    Tolerates responses wrapped in Markdown code fences or surrounded by stray
    prose by falling back to the first ``{ ... }`` span. Raises
    :class:`InvalidJSONError` if no valid JSON object can be recovered.
    """

    if text is None or not text.strip():
        raise InvalidJSONError("LLM response was empty; expected a JSON object.")

    candidate = text.strip()

    # Strip Markdown code fences (```json ... ``` or ``` ... ```).
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.lower().startswith("json"):
            candidate = candidate[4:]
        candidate = candidate.strip()

    try:
        return _as_object(json.loads(candidate))
    except (json.JSONDecodeError, InvalidJSONError):
        pass

    # Fallback: grab the outermost {...} span.
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return _as_object(json.loads(candidate[start : end + 1]))
        except json.JSONDecodeError as exc:
            raise InvalidJSONError(f"Could not parse JSON from LLM response: {exc}") from exc

    raise InvalidJSONError("No JSON object found in LLM response.")


def _as_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidJSONError("Expected a JSON object at the top level.")
    return value
