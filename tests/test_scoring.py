from costroute.scoring import parse_json, score, well_formed

J = {"origin": "Fenmoor", "destination": "Westlin", "weight_kg": 420}


def test_extract_id():
    assert score("extract_id", "LF-12345-A", "LF-12345-A")
    assert not score("extract_id", "LF-12345-A or LF-99999-B", "LF-12345-A")
    assert not score("extract_id", "LF-99999-B", "LF-12345-A")


def test_intent_needs_exactly_one_label():
    assert score("intent", "delivery_delay", "delivery_delay")
    assert score("intent", "Delivery delay.", "delivery_delay")
    assert not score("intent", "billing or damage", "billing")


def test_numbers_and_dates():
    assert score("arith1", "1,032", "1032") and not score("arith1", "about 1000", "1032")
    assert score("date_calc", "2026-04-09", "2026-04-09") and not score("date_calc", "April 9", "2026-04-09")


def test_json_extract():
    assert score("json_extract", '{"origin": "Fenmoor", "destination": "Westlin", "weight_kg": "420 kg"}', J)
    assert not score("json_extract", '{"origin": "Westlin", "destination": "Fenmoor", "weight_kg": 420}', J)
    assert not score("json_extract", "origin Fenmoor", J)


def test_parse_json_rejects_non_objects_and_garbage():
    assert parse_json("[1, 2]") is None and parse_json("{bad json}") is None


def test_well_formed_is_answer_free():
    assert well_formed("arith2", "504") and not well_formed("arith2", "I think it is probably five hundred")
    assert well_formed("json_extract", '{"origin": "a", "destination": "b", "weight_kg": 1}')
    assert not well_formed("json_extract", '{"origin": "a"}')
    assert not well_formed("date_calc", "") and not well_formed("intent", "billing, damage")
