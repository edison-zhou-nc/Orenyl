from orenyl.domain_registry import normalize_domain


def test_normalize_alias_and_custom_domain():
    assert normalize_domain("medical") == "health"
    assert normalize_domain("travel") == "travel"
