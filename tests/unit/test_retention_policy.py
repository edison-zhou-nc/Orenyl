from lore.retention import apply_retention_policies


def test_retention_policy_transitions_by_age():
    events = [
        {"id": "e1", "ts": "2026-01-01T00:00:00Z", "domains": ["health"], "retention_tier": "hot"},
        {"id": "e2", "ts": "2026-01-05T00:00:00Z", "domains": ["health"], "retention_tier": "warm"},
    ]
    out = apply_retention_policies(
        events=events,
        now_ts="2026-01-10T00:00:00Z",
        policies={"health": {"warm_days": 1, "archive_days": 3, "delete_days": 7}},
    )

    assert out["tiers"]["e1"] == "delete"
    assert out["tiers"]["e2"] == "archive"


def test_retention_policy_uses_most_conservative_domain_policy():
    events = [
        {"id": "e1", "ts": "2026-01-01T00:00:00Z", "domains": ["health", "career"]},
    ]
    out = apply_retention_policies(
        events=events,
        now_ts="2026-01-10T00:00:00Z",
        policies={
            "health": {"warm_days": 20, "archive_days": 30, "delete_days": 60},
            "career": {"warm_days": 1, "archive_days": 3, "delete_days": 7},
        },
    )
    assert out["tiers"]["e1"] == "delete"
