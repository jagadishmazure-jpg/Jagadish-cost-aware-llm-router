import re
from collections import Counter

from costroute.tasks import FAMILIES, build_tasks, split_of

TASKS = build_tasks()


def test_bank_size_and_balance():
    assert len(TASKS) == 600 and set(Counter(t["family"] for t in TASKS).values()) == {100}


def test_ids_unique_and_generation_deterministic():
    assert len({t["task_id"] for t in TASKS}) == 600
    assert build_tasks() == TASKS


def test_split_is_by_hash_and_roughly_60_20_20():
    c = Counter(t["split"] for t in TASKS)
    assert 320 <= c["train"] <= 400 and 90 <= c["val"] <= 150 and 90 <= c["test"] <= 150
    assert all(split_of(t["task_id"]) == t["split"] for t in TASKS)


def test_every_family_is_in_test():
    assert {t["family"] for t in TASKS if t["split"] == "test"} == set(FAMILIES)


def test_personal_data_only_in_text_families_and_fictional():
    pii = [t for t in TASKS if t["has_pii"]]
    assert pii and {t["family"] for t in pii} <= {"extract_id", "intent"}
    for t in pii:
        assert "@example.com" in t["prompt"] or re.search(r"\+44 7700 900\d{3}", t["prompt"])


def test_reference_answers_are_consistent():
    for t in TASKS:
        if t["family"] == "arith2":
            a, b, c = map(int, re.findall(r"\d+", t["prompt"])[:3])
            assert t["answer"] == str(a * b - c)
        if t["family"] == "extract_id":
            assert t["answer"] in t["prompt"]


def test_personal_data_count_matches_detector():
    from costroute.guardrails import has_personal_data

    assert sum(t["has_pii"] for t in TASKS) == 42
    assert all(has_personal_data(t["prompt"]) == t["has_pii"] for t in TASKS)
