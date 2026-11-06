"""Settings, read from environment variables.

A `.env` file in the project root is loaded if it exists (real environment variables win).
`.env` is git-ignored: API keys must never be committed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def _get(name: str, default: str = "") -> str:
    """Environment value, or `default` when the variable is unset or blank."""
    value = os.environ.get(name, "").strip()
    return value or default


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # Identity shown on /v1/metadata (the leaderboard reads this).
    team_name: str = "unnamed-team"
    team_members: list[str] = field(default_factory=list)
    contact_email: str = ""
    version: str = "0.1.0"
    approach: str = "context-grounded composer (in development)"

    # LLM (Gemini free tier). With no key the bot must run on deterministic templates only.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            team_name=_get("TEAM_NAME", cls.team_name),
            team_members=_csv(_get("TEAM_MEMBERS")),
            contact_email=_get("CONTACT_EMAIL"),
            version=_get("BOT_VERSION", cls.version),
            approach=_get("BOT_APPROACH", cls.approach),
            gemini_api_key=_get("GEMINI_API_KEY"),
            gemini_model=_get("GEMINI_MODEL", cls.gemini_model),
        )
