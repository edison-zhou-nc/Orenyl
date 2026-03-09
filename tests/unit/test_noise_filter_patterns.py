from lore.noise_filter import should_store


def test_rejects_keys_cards_and_agent_refusals():
    assert should_store("sk-abc123")[0] is False
    assert should_store("ghp_xxx")[0] is False
    assert should_store("xoxb-111-222")[0] is False
    assert should_store("4111 1111 1111 1111")[0] is False
    assert should_store("I don't have enough information to answer that")[0] is False
