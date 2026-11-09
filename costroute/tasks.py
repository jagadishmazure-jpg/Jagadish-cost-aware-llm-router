"""Synthetic task bank for a fictional freight company, Lumenfield Freight.

Six request families that an internal operations assistant gets. Every task has a known reference
answer, so quality is scored by code (no LLM judge). Generation is seeded and deterministic.
About one in five extraction and intent tasks carry synthetic personal data (an e-mail or phone
number), which the residency guardrail must keep on the local tier.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import random

FAMILIES = ("extract_id", "intent", "arith1", "arith2", "json_extract", "date_calc")
INTENTS = ("billing", "delivery_delay", "damage", "address_change", "cancellation")
CITIES = ["Brackwell", "Fenmoor", "Ostridge", "Calder Point", "Harrowgate", "Lindqvist Bay", "Marrowby",
          "Pellham", "Quenford", "Rookhaven", "Saltmere", "Thornbury Cross", "Umbervale", "Westlin"]
NAMES = ["Asha Ren", "Bo Calloway", "Dara Mbeki", "Eli Novak", "Farah Quist", "Gus Tamura", "Ines Vale",
         "Jon Okoro", "Kai Lindell", "Lena Ruiz", "Milo Sato", "Nia Brandt"]
SYSTEM = "You are an operations assistant. Reply with only the final answer. No explanation."

INTENT_TEMPLATES = {
    "billing": ["I was charged twice for invoice {ref}, can someone check?",
                "The amount on invoice {ref} is higher than the quote we agreed.",
                "Please send a corrected bill for {ref}; the VAT looks wrong.",
                "Why does my statement show a fee for {ref} that I never ordered?"],
    "delivery_delay": ["Shipment {ref} was due on Monday and still has not arrived.",
                       "Our pallets on {ref} are three days late, where are they?",
                       "Tracking for {ref} has not moved since last week.",
                       "The driver for {ref} never showed up for the delivery slot."],
    "damage": ["Two cartons on {ref} arrived crushed and wet.",
               "The fridge delivered under {ref} has a dented door.",
               "Half the glass jars in {ref} were broken on arrival.",
               "Pallet {ref} was delivered with the shrink wrap torn and items missing."],
    "address_change": ["Please deliver {ref} to our new warehouse instead of the old site.",
                       "We moved offices, can you update the drop-off for {ref}?",
                       "Redirect {ref} to the depot in {city}, the customer is away.",
                       "The postcode on {ref} is wrong, it should go to the {city} branch."],
    "cancellation": ["Please cancel order {ref}, we no longer need it.",
                     "We want to stop {ref} before it leaves the depot.",
                     "Call off the pickup for {ref}, the client cancelled.",
                     "Withdraw booking {ref} and refund the deposit please."],
}


def _ref(rng: random.Random) -> str:
    return f"LF-{rng.randint(10000, 99999)}-{rng.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}"


def _pii(rng: random.Random) -> str:
    name = rng.choice(NAMES)
    if rng.random() < 0.5:
        return f" Contact {name} at {name.split()[0].lower()}.{rng.randint(10, 99)}@example.com."
    return f" Call {name} on +44 7700 900{rng.randint(100, 999)}."  # UK range reserved for fiction


def _task(family: str, i: int) -> dict:
    rng = random.Random(int(hashlib.sha256(f"{family}-{i}".encode()).hexdigest()[:8], 16))
    pii = False
    if family == "extract_id":
        ref, city = _ref(rng), rng.choice(CITIES)
        other = _ref(rng)
        filler = rng.choice(["The driver noted a late arrival.", "Customs cleared it yesterday.",
                             "It replaces the earlier booking.", "Two pallets were re-labelled."])
        body = (f"Depot note from {city}: consignment {ref} is on bay {rng.randint(1, 40)}. {filler} "
                f"Do not confuse it with return {other}.")
        if rng.random() < 0.2:
            body += _pii(rng)
            pii = True
        prompt = f"{body}\nQuestion: What is the consignment reference? Answer with the reference only."
        answer = ref
    elif family == "intent":
        label = INTENTS[i % len(INTENTS)]
        text = rng.choice(INTENT_TEMPLATES[label]).format(ref=_ref(rng), city=rng.choice(CITIES))
        if rng.random() < 0.2:
            text += _pii(rng)
            pii = True
        prompt = (f"Customer message: \"{text}\"\nClassify the message as exactly one of: "
                  f"{', '.join(INTENTS)}. Answer with the label only.")
        answer = label
    elif family == "arith1":
        a, b = rng.randint(6, 48), rng.randint(3, 19)
        unit = rng.choice(["boxes", "crates", "drums", "sacks"])
        prompt = f"A pallet holds {a} {unit}. How many {unit} are on {b} pallets? Answer with a number only."
        answer = str(a * b)
    elif family == "arith2":
        a, b, c = rng.randint(8, 30), rng.randint(12, 40), rng.randint(5, 60)
        prompt = (f"A truck carries {a} pallets with {b} boxes on each. {c} boxes are damaged and returned. "
                  f"How many good boxes are delivered? Answer with a number only.")
        answer = str(a * b - c)
    elif family == "json_extract":
        o, d = rng.sample(CITIES, 2)
        w = rng.randint(120, 9800)
        lead = rng.choice(["Booking confirmed:", "New load:", "Haulage request:", "Transfer order:"])
        prompt = (f"{lead} {w} kg of goods collected in {o} for delivery to {d} on vehicle "
                  f"{rng.randint(100, 999)}.\nReturn JSON with keys origin, destination, weight_kg. JSON only.")
        answer = {"origin": o, "destination": d, "weight_kg": w}
    elif family == "date_calc":
        start = dt.date(2026, 1, 1) + dt.timedelta(days=rng.randint(0, 330))
        days = rng.randint(3, 40)
        prompt = (f"An order ships on {start.isoformat()} and transit takes {days} calendar days. "
                  f"On what date does it arrive? Answer in YYYY-MM-DD only.")
        answer = (start + dt.timedelta(days=days)).isoformat()
    else:
        raise ValueError(f"unknown family {family}")
    return {"task_id": f"{family}-{i:03d}", "family": family, "prompt": prompt, "answer": answer,
            "has_pii": pii, "split": split_of(f"{family}-{i:03d}")}


def split_of(task_id: str) -> str:
    """60/20/20 train/val/test by hash of the task id."""
    h = int(hashlib.sha256(f"split|{task_id}".encode()).hexdigest()[:8], 16) % 100
    return "train" if h < 60 else "val" if h < 80 else "test"


def build_tasks(per_family: int = 100) -> list[dict]:
    return [_task(f, i) for f in FAMILIES for i in range(per_family)]
