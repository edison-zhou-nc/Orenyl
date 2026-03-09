from lore.domain_registry import should_promote_domain


def test_custom_domain_promotion_threshold():
    assert should_promote_domain(event_count=10) is True
    assert should_promote_domain(event_count=9) is False
