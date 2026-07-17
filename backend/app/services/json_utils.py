"""Helpers for extracting JSON from (possibly noisy) LLM responses."""

from __future__ import annotations

import json
import re
from typing import Any

from ..errors import InvalidJSONError


def extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from ``text``.

    Tolerates responses wrapped in Markdown code fences or surrounded by stray
    prose by falling back to the first ``{ ... }`` span.  Attempts to repair
    common LLM JSON mistakes (trailing commas, single quotes, unquoted keys,
    missing commas) before raising :class:`InvalidJSONError`.
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

    # Direct parse.
    result = _try_parse(candidate)
    if result is not None:
        return result

    # Fallback: grab the outermost {...} span.
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        inner = candidate[start : end + 1]
        result = _try_parse(inner)
        if result is not None:
            return result

    # Final fallback: repair then try the outermost span again.
    if start != -1 and end != -1 and end > start:
        inner = candidate[start : end + 1]
        repaired = _repair_json(inner)
        result = _try_parse(repaired)
        if result is not None:
            return result

    raise InvalidJSONError("Could not parse JSON from LLM response.")


def _try_parse(text: str) -> dict[str, Any] | None:
    """Try ``json.loads`` and return the dict, or ``None`` on failure."""
    try:
        return _as_object(json.loads(text))
    except (json.JSONDecodeError, InvalidJSONError):
        return None


def _repair_json(text: str) -> str:
    """Attempt to fix common JSON formatting issues from LLM output.

    Performs (in order):
      1. Remove JavaScript-style comments (// and /* */).
      2. Replace single quotes with double quotes around keys and string values.
      3. Remove trailing commas before ``]`` and ``}``.
      4. Insert missing commas between object properties and array elements.
      5. Wrap unquoted property names (``{key:`` → ``{"key":``).
    """
    # 1. Remove single-line comments (// ...) — inline and whole-line.
    text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    # Remove block comments (/* ... */).
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    # 2. Replace single-quoted strings with double-quoted strings.
    #    Match '...' but not inside double-quoted strings.
    text = _replace_single_quotes(text)

    # 3. Trailing commas — remove commas before ] or }.
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # 4. Wrap unquoted object keys (JavaScript shorthand).
    #    Pattern: {key: or ,key: where key is word chars.
    text = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z_0-9]*)\s*:", r'\1"\2":', text)

    # 5. Insert missing commas between properties/array elements.
    #    After a value-ender (" or } or ] or number/bool/null) followed by
    #    whitespace and a new property " or array element, insert a comma.
    #    Match positions where no comma exists between ``"..."`` ``"..."``.
    text = _insert_missing_commas(text)

    return text


def _replace_single_quotes(text: str) -> str:
    """Convert single-quoted strings to double-quoted, handling escapes."""
    result: list[str] = []
    i = 0
    in_double = False
    in_single = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        # Toggle string state, respecting backslash escapes.
        if ch == "\\":
            if in_double or in_single:
                result.extend([ch, nxt])
                i += 2
                continue
        if ch == '"' and not in_single:
            in_double = not in_double
            result.append(ch)
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            result.append('"')
            i += 1
            continue

        result.append(ch)
        i += 1
    return "".join(result)


def _insert_missing_commas(text: str) -> str:
    """Insert commas where they appear to be missing between JSON elements.

    Uses only safe patterns that won't corrupt string values:
      - Between ``}`` and ``{`` (missing comma between nested objects)
      - Between ``]`` and ``"`` (array closing before next property)
      - Between ``"`` and ``"`` when separated by whitespace (properties)
        but only when the second ``"`` is followed by ``:`` (object key).
    """
    # Case A: } followed by { — add comma.
    text = re.sub(r"}(\s*){", r"},\1{", text)

    # Case B: ] followed by " — add comma (array value before next key).
    # NOTE: raw strings with \" produce a literal backslash, so use '' quotes
    # to keep the replacement clean.
    text = re.sub(r'](\s+)"', r'],\1"', text)

    # Case C: closing " then ws then "key": — add comma.
    # Lookahead confirms the second " starts a key name ending with ":
    text = re.sub(
        r'"\s+(?="[A-Za-z_][A-Za-z_0-9]*"\s*:)',
        r'", ',
        text,
    )

    # Case D: number/bool/null then ws then "key": — add comma.
    text = re.sub(
        r'(?<=[0-9tfn}])\s+(?="[A-Za-z_][A-Za-z_0-9]*"\s*:)',
        r', ',
        text,
    )

    return text


def _as_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidJSONError("Expected a JSON object at the top level.")
    return value
