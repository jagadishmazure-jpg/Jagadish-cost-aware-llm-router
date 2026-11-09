"""Azure ML / Microsoft Foundry scoring script for the router. WRITTEN, NOT RUN in Azure.

init() trains the quality predictor from the committed task bank and measured runs (no pickle).
run() accepts {"prompt": "..."} and returns the routing decision only: which model to call and why.
Calling the chosen model is the caller's job (each tier is its own endpoint in the deployment design).
"""

from __future__ import annotations

import json
import logging

from costroute import service

log = logging.getLogger("costroute.score")


def init() -> None:
    service.default_router()
    log.info("router ready")


def run(raw_data: str) -> dict:
    try:
        payload = json.loads(raw_data)
    except (TypeError, json.JSONDecodeError):
        return {"error": "body must be JSON like {\"prompt\": \"...\"}"}
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "field 'prompt' (non-empty string) is required"}
    try:
        decision = service.route(prompt)
    except ValueError as e:
        return {"error": str(e)}
    log.info("routed to %s (residency_local=%s)", decision["model"], decision["local_only"])
    return decision
