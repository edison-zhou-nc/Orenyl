from lore.noise_filter import should_store


def test_rejects_secrets_and_allows_normal_content():
    ok, _ = should_store("I started metformin")
    assert ok is True

    ok, reason = should_store("password: hunter2")
    assert ok is False
    assert "credential" in reason.lower() or "password" in reason.lower()
