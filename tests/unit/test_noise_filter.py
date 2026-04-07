from orenyl.noise_filter import should_store


def test_rejects_secrets_and_allows_normal_content():
    ok, _ = should_store("I started metformin")
    assert ok is True

    ok, reason = should_store("password: hunter2")
    assert ok is False
    assert "credential" in reason.lower() or "password" in reason.lower()


def test_rejects_aws_access_keys_private_keys_jwts_and_bearer_tokens():
    samples = [
        "AWS key AKIA1234567890ABCDEF should never be stored",
        "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdef1234567890.zyxwvu9876543210",
        "token=eyJhbGciOiJIUzI1NiJ9.abcdef1234567890.zyxwvu9876543210",
    ]

    for sample in samples:
        ok, reason = should_store(sample)
        assert ok is False
        assert reason == "sensitive_credential_or_identifier"
