"""File-based prompt loading.

Prompts live under ``backend/prompts/<name>/{system,user}.md`` and are NEVER
hardcoded in Python. Each loaded template carries a deterministic ``version``
(derived from its content) so it can be logged with every LLM call.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# backend/app/services/prompts.py -> parents[2] == backend/
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class PromptError(Exception):
    """Raised when a prompt cannot be loaded."""


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    system: str
    user: str
    version: str

    def render_user(self, variables: dict[str, str]) -> str:
        """Fill ``{{placeholder}}`` tokens in the user template.

        Uses explicit ``{{token}}`` replacement (not ``str.format``) so JSON braces
        inside the prompt are left untouched.
        """

        rendered = self.user
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
        return rendered


def _read(path: Path) -> str:
    if not path.is_file():
        raise PromptError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache
def load_prompt(name: str) -> PromptTemplate:
    """Load and cache the prompt template identified by ``name``."""

    base = PROMPTS_DIR / name
    system = _read(base / "system.md")
    user = _read(base / "user.md")
    digest = hashlib.sha256(f"{system}\n---\n{user}".encode()).hexdigest()[:12]
    return PromptTemplate(name=name, system=system, user=user, version=f"{name}@{digest}")
