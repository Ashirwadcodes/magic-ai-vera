"""Request bodies for the judge's calls.

Deliberately lenient: unknown fields are kept, optional fields default. A 422 here would
look like a broken bot to the harness, so we only reject what we truly cannot use.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="allow")


class ContextPush(_Lenient):
    scope: str
    context_id: str
    version: int
    payload: dict[str, Any]
    delivered_at: str | None = None


class TickRequest(_Lenient):
    now: str | None = None
    available_triggers: list[str] = Field(default_factory=list)


class ReplyRequest(_Lenient):
    conversation_id: str
    merchant_id: str | None = None
    customer_id: str | None = None
    from_role: str = "merchant"
    message: str = ""
    received_at: str | None = None
    turn_number: int = 1
