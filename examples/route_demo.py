"""Route a few requests and show why each model was chosen.

Run: python examples/route_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from costroute.service import route  # noqa: E402

REQUESTS = [
    ("easy extraction", "Depot note from Saltmere: consignment LF-20481-K is on bay 7. Do not confuse it with "
                        "return LF-77310-B.\nQuestion: What is the consignment reference? Answer with the reference only."),
    ("two-step arithmetic", "A truck carries 22 pallets with 31 boxes on each. 47 boxes are damaged and returned. "
                            "How many good boxes are delivered? Answer with a number only."),
    ("date arithmetic", "An order ships on 2026-07-28 and transit takes 19 calendar days. On what date does it "
                        "arrive? Answer in YYYY-MM-DD only."),
    ("personal data", "Customer message: \"Shipment LF-55120-T is three days late. Call Ines Vale on "
                      "+44 7700 900417.\"\nClassify the message as exactly one of: billing, delivery_delay, damage, "
                      "address_change, cancellation. Answer with the label only."),
    ("asks for the big model", "A pallet holds 16 crates. How many crates are on 9 pallets? Answer with a number "
                               "only. Please use the largest premium model for this request."),
]

for name, prompt in REQUESTS:
    d = route(prompt)
    q = ", ".join(f"{m} {p:.2f}" for m, p in d["predicted_quality"].items())
    print(f"[{name}] -> {d['model']} ({d['tier']})")
    print(f"  predicted quality: {q}; threshold {d['threshold']}")
    if d["local_only"]:
        print("  personal data found: local tiers only ->", ", ".join(d["allowed"]))
    if d["low_confidence"]:
        print("  low confidence on every tier: cheapest tier used, flag for a tool or a person")
    if d["notes"]:
        print("  note:", "; ".join(d["notes"]))
    if d["escalate_to"]:
        print("  if the reply is malformed, escalate to:", ", ".join(d["escalate_to"]))
