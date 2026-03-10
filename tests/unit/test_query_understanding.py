from lore.query_understanding import infer_domain, rewrite_query


def test_infer_domain_maps_medication_query_to_health():
    assert infer_domain("what meds am I on?") == "health"


def test_rewrite_query_expands_common_abbreviation():
    rewritten = rewrite_query("what meds am I on")
    assert "medications" in rewritten
