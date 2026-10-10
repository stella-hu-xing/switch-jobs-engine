"""Single LLM access point: a thin wrapper around OpenRouter's OpenAI-compatible API.

Design notes
------------
* Model selection per task via :class:`ModelTier` -- cheap model for parsing/
  normalization, stronger model for tailoring/interview prep.
* ``complete_json`` asks for JSON and tolerates fenced/chatty responses.
* When ``OPENROUTER_API_KEY`` is unset the client runs in **offline mode** and
  returns deterministic stub output, so the whole skeleton is runnable and
  testable without spending tokens.
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum
from typing import Any

from app.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class ModelTier(str, Enum):
    FAST = "fast"
    SMART = "smart"


class LLMError(RuntimeError):
    """Raised when the LLM call fails or returns unusable content."""


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: Any | None = None

    # ---------------------------------------------------------------- internals
    @property
    def offline(self) -> bool:
        return self.settings.llm_offline

    def model_for(self, tier: ModelTier | str) -> str:
        tier = ModelTier(tier)
        if tier is ModelTier.SMART:
            return self.settings.openrouter_model_smart
        return self.settings.openrouter_model_fast

    def _openai(self) -> Any:
        if self._client is None:
            from openai import OpenAI  # lazy import keeps startup fast

            self._client = OpenAI(
                api_key=self.settings.openrouter_api_key,
                base_url=self.settings.openrouter_base_url,
                timeout=self.settings.llm_timeout_seconds,
                max_retries=self.settings.llm_max_retries,
            )
        return self._client

    # ------------------------------------------------------------------- public
    def complete(
        self,
        *,
        system: str,
        user: str,
        tier: ModelTier | str = ModelTier.FAST,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        """Return raw text from the model (or a deterministic stub when offline)."""
        if self.offline:
            return _offline_text(system=system, user=user, json_mode=json_mode)

        kwargs: dict[str, Any] = {
            "model": self.model_for(tier),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self._openai().chat.completions.create(**kwargs)
        except Exception as exc:  # pragma: no cover - network path
            raise LLMError(f"OpenRouter call failed: {exc}") from exc

        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise LLMError("OpenRouter returned empty content")
        return content

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        tier: ModelTier | str = ModelTier.FAST,
        temperature: float = 0.1,
        fallback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call the model and parse a JSON object out of the reply.

        When offline, the generic stub payload is never returned to callers:
        each call site's own schema-shaped ``fallback`` is used instead, so
        offline/dev runs produce consistent, schema-valid output everywhere.
        """
        if self.offline:
            return fallback if fallback is not None else _offline_json_payload()

        raw = self.complete(
            system=system, user=user, tier=tier, temperature=temperature, json_mode=True
        )
        parsed = extract_json_object(raw)
        if parsed is None:
            if fallback is not None:
                logger.warning("LLM JSON parse failed; using fallback payload")
                return fallback
            raise LLMError(f"Could not parse JSON from model output: {raw[:400]}")
        return parsed


def extract_json_object(raw: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON object from a possibly chatty reply."""
    candidates: list[str] = [raw]
    fenced = _JSON_FENCE_RE.search(raw)
    if fenced:
        candidates.insert(0, fenced.group(1))
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            value = json.loads(candidate.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _offline_json_payload() -> dict[str, Any]:
    return {
        "offline_stub": True,
        "note": "OPENROUTER_API_KEY is not set and no fallback was provided by the caller.",
    }


def _offline_text(*, system: str, user: str, json_mode: bool) -> str:
    """Deterministic placeholder output for offline/dev/test runs."""
    if json_mode:
        return json.dumps(
            {
                "offline_stub": True,
                "note": (
                    "OPENROUTER_API_KEY is not set, so this payload is a deterministic "
                    "stub. Set the key to get real LLM output."
                ),
                "system_prompt_chars": len(system),
                "input_chars": len(user),
            }
        )
    return (
        "[offline-stub] OPENROUTER_API_KEY is not configured, so no LLM call was made. "
        f"Received {len(user)} characters of input."
    )


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """FastAPI dependency returning the process-wide LLM client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def set_llm_client(client: LLMClient | None) -> None:
    """Override the client (used by tests)."""
    global _client
    _client = client
