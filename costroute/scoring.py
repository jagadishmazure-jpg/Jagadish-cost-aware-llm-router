"""Reference-based quality scoring. Deterministic: no LLM judge, so labels cannot drift."""

from __future__ import annotations

import json
import re

from .tasks import INTENTS

_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_REF = re.compile(r"LF-\d{5}-[A-Z]")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", " ", s.lower()).strip()


def first_number(text: str) -> str | None:
    m = _NUM.search(text)
    return m.group(0).replace(",", "") if m else None


def parse_json(text: str) -> dict | None:
    """First {...} block that parses as a JSON object, else None."""
    m = re.search(r"\{.*?\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def score(family: str, output: str, answer) -> bool:
    out = output.strip()
    if family == "extract_id":
        refs = _REF.findall(out.upper())
        return len(set(refs)) == 1 and refs[0] == answer
    if family == "intent":
        found = [lab for lab in INTENTS if lab in _norm(out).replace(" ", "_") or lab.replace("_", " ") in _norm(out)]
        return found == [answer]
    if family in ("arith1", "arith2"):
        return first_number(out) == answer
    if family == "date_calc":
        d = _DATE.findall(out)
        return bool(d) and d[0] == answer
    if family == "json_extract":
        obj = parse_json(out)
        if obj is None:
            return False
        try:
            w = int(float(str(obj.get("weight_kg", "")).replace(",", "").replace("kg", "").strip()))
        except ValueError:
            return False
        return (str(obj.get("origin", "")).strip().lower() == answer["origin"].lower()
                and str(obj.get("destination", "")).strip().lower() == answer["destination"].lower()
                and w == answer["weight_kg"])
    raise ValueError(f"unknown family {family}")


def well_formed(family: str, output: str) -> bool:
    """Cheap format check the router can run on a reply *without* knowing the answer (for escalation)."""
    out = output.strip()
    if not out:
        return False
    if family == "extract_id":
        return len(set(_REF.findall(out.upper()))) == 1
    if family == "intent":
        return sum(lab in _norm(out).replace(" ", "_") for lab in INTENTS) == 1
    if family in ("arith1", "arith2"):
        return first_number(out) is not None and len(out) < 40
    if family == "date_calc":
        return len(_DATE.findall(out)) == 1
    if family == "json_extract":
        obj = parse_json(out)
        return obj is not None and {"origin", "destination", "weight_kg"} <= set(obj)
    return False
