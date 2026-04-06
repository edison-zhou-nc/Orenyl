from orenyl.noise_filter import should_store


def test_rejects_keys_cards_and_agent_refusals():
    assert should_store("sk-abc123")[0] is False
    assert should_store("ghp_xxx")[0] is False
    assert should_store("xoxb-111-222")[0] is False
    assert should_store("4111 1111 1111 1111")[0] is False
    assert should_store("I don't have enough information to answer that")[0] is False


def test_rejects_email_phone_and_connection_strings():
    assert should_store("contact me at user@example.com for access details")[0] is False
    assert should_store("call me at +1 555 222 1111 after the deploy")[0] is False
    assert should_store("postgres://user:pass@db.internal/app is the backup DSN")[0] is False
