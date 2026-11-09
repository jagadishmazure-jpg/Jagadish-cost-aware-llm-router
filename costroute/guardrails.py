"""Guardrails that run before and around routing.

1. Residency: prompts with personal data (e-mail or phone, detected by pattern) may only use tiers
   marked local. In the deployment design the large tier is a Microsoft Foundry endpoint, so it is
   not local.
2. Routing directives inside the prompt ("use the biggest model") are removed before the router
   sees the text, so a user cannot buy a more expensive tier by asking.
3. Input size cap.
4. Budget cap per batch: when the next request would overrun, downgrade to the cheapest allowed
   tier; when even that would overrun, refuse with a clear reason.
5. Circuit breaker per tier with fallback to the next allowed tier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_CHARS = 8000
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE = re.compile(r"(?<![\w-])(?:\+\d{1,3}|0)(?:[ -]?\d{2,5}){2,4}(?![\w-])")  # +44 7700 900123, 07700 900123
DIRECTIVE = re.compile(r"[^.?!\n]*\b(use|route|send|switch)\b[^.?!\n]*\b(model|tier|gpt|largest|biggest|premium)\b"
                       r"[^.?!\n]*[.?!\n]?", re.I)
LOCAL_TIERS = {"small", "medium"}


class GuardrailError(ValueError):
    pass


def has_personal_data(text: str) -> bool:
    return bool(EMAIL.search(text) or PHONE.search(text))


def sanitize(text: str) -> tuple[str, list[str]]:
    if not isinstance(text, str):
        raise GuardrailError("prompt must be a string")
    notes = []
    if len(text) > MAX_CHARS:
        raise GuardrailError(f"prompt longer than {MAX_CHARS} characters")
    clean = DIRECTIVE.sub("", text)
    if clean != text:
        notes.append("removed a routing directive from the prompt")
    return clean.strip(), notes


def allowed_models(text: str, tiers: dict[str, str]) -> list[str]:
    """Models this prompt may use, cheapest first. `tiers` maps model -> tier name."""
    if has_personal_data(text):
        return [m for m, t in tiers.items() if t in LOCAL_TIERS]
    return list(tiers)


@dataclass
class Budget:
    cap_usd: float
    spent_usd: float = 0.0
    refused: int = 0
    downgraded: int = 0

    def __post_init__(self):
        if self.cap_usd <= 0:
            raise GuardrailError("budget cap must be positive")

    def remaining(self) -> float:
        return self.cap_usd - self.spent_usd

    def charge(self, usd: float) -> None:
        if usd > self.remaining() + 1e-12:
            raise GuardrailError("charge would exceed the budget cap")
        self.spent_usd += usd


@dataclass
class CircuitBreaker:
    """Opens after `threshold` consecutive failures; closes again after `cooldown` skipped calls."""

    threshold: int = 3
    cooldown: int = 5
    failures: dict[str, int] = field(default_factory=dict)
    open_for: dict[str, int] = field(default_factory=dict)

    def available(self, model: str) -> bool:
        left = self.open_for.get(model, 0)
        if left > 0:
            self.open_for[model] = left - 1
            return False
        return True

    def record(self, model: str, ok: bool) -> None:
        if ok:
            self.failures[model] = 0
            return
        self.failures[model] = self.failures.get(model, 0) + 1
        if self.failures[model] >= self.threshold:
            self.open_for[model] = self.cooldown
            self.failures[model] = 0
