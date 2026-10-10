"""Prompt template registry.

Templates live as ``.md`` files under ``app/prompts/templates`` so they can be
edited/reviewed without touching code. Use ``render("profile_extract", **vars)``
with ``{placeholder}``-style substitution.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from string import Template

TEMPLATE_DIR = Path(__file__).parent / "templates"


class PromptNotFound(KeyError):
    pass


@lru_cache
def load(name: str) -> str:
    path = TEMPLATE_DIR / f"{name}.md"
    if not path.exists():
        raise PromptNotFound(f"No prompt template named '{name}' in {TEMPLATE_DIR}")
    return path.read_text(encoding="utf-8")


def render(name: str, **variables: object) -> str:
    """Render a template; ``$`` placeholders are substituted safely."""
    return Template(load(name)).safe_substitute(
        {k: ("" if v is None else str(v)) for k, v in variables.items()}
    )


def available() -> list[str]:
    return sorted(p.stem for p in TEMPLATE_DIR.glob("*.md"))
