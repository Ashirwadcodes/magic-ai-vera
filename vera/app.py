"""HTTP surface of the bot: the endpoints the judge harness calls.

    POST /v1/context   receive a context push (idempotent by scope + id + version)
    POST /v1/tick      periodic wake-up; the bot may start conversations
    POST /v1/reply     the merchant/customer answered; the bot sends, waits or ends
    GET  /v1/healthz   liveness (3 failures in a row = disqualified)
    GET  /v1/metadata  team identity for the leaderboard

`tick` and `reply` are placeholders in this step; the composer arrives in later steps.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .models import ContextPush, ReplyRequest, TickRequest
from .store import SCOPES, ContextStore

log = logging.getLogger("vera")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an app with its own empty store (tests get a fresh one each time)."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = settings or Settings.from_env()
    store = ContextStore()
    started = time.monotonic()
    started_at = _utc_now()

    app = FastAPI(title="Vera bot", version=settings.version)
    app.state.settings = settings
    app.state.store = store

    @app.exception_handler(RequestValidationError)
    async def _invalid_request(request: Request, exc: RequestValidationError):
        # The testing brief asks for a 400 with {"accepted": false, ...} on a bad context push.
        if request.url.path == "/v1/context":
            problems = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
            return JSONResponse(
                status_code=400,
                content={"accepted": False, "reason": "malformed_request", "details": problems},
            )
        return await request_validation_exception_handler(request, exc)

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def root():
        return {"service": "vera-bot", "status": "ok"}

    # HEAD is allowed because free uptime monitors (e.g. UptimeRobot) ping with HEAD by default.
    @app.api_route("/v1/healthz", methods=["GET", "HEAD"])
    async def healthz():
        return {
            "status": "ok",
            "uptime_seconds": int(time.monotonic() - started),
            "contexts_loaded": store.counts(),
        }

    @app.get("/v1/metadata")
    async def metadata():
        return {
            "team_name": settings.team_name,
            "team_members": settings.team_members,
            "model": settings.gemini_model,
            "approach": settings.approach,
            "contact_email": settings.contact_email,
            "version": settings.version,
            "submitted_at": started_at,
        }

    @app.post("/v1/context")
    async def push_context(body: ContextPush):
        if body.scope not in SCOPES:
            return JSONResponse(
                status_code=400,
                content={
                    "accepted": False,
                    "reason": "invalid_scope",
                    "details": f"scope must be one of {list(SCOPES)}, got {body.scope!r}",
                },
            )
        result = store.put(body.scope, body.context_id, body.version, body.payload)
        if result.outcome == "stale":
            return JSONResponse(
                status_code=409,
                content={"accepted": False, "reason": "stale_version", "current_version": result.version},
            )
        log.debug("context %s %s v%s -> %s", body.scope, body.context_id, body.version, result.outcome)
        return {
            "accepted": True,
            "ack_id": f"ack_{body.scope}_{body.context_id}_v{result.version}",
            "stored_at": _utc_now(),
        }

    @app.post("/v1/tick")
    async def tick(body: TickRequest):
        # Placeholder: staying silent is a valid answer ("restraint is rewarded").
        return {"actions": []}

    @app.post("/v1/reply")
    async def reply(body: ReplyRequest):
        # Placeholder until the reply state machine exists.
        return {"action": "wait", "wait_seconds": 1800, "rationale": "reply handling not built yet"}

    return app


app = create_app()
