from orenyl.config import semantic_dedup_threshold_for_domains


def test_health_domain_threshold_override(monkeypatch):
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_DEFAULT", "0.92")
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_HEALTH", "0.97")
    threshold = semantic_dedup_threshold_for_domains(["health"])
    assert threshold == 0.97


def test_domain_threshold_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_DEFAULT", "0.91")
    threshold = semantic_dedup_threshold_for_domains(["career"])
    assert threshold == 0.91


def test_domain_threshold_can_be_lower_than_default(monkeypatch):
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_DEFAULT", "0.95")
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_HEALTH", "0.8")
    threshold = semantic_dedup_threshold_for_domains(["health"])
    assert threshold == 0.8


def test_multi_domain_uses_strictest_threshold_independent_of_order(monkeypatch):
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_DEFAULT", "0.9")
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_HEALTH", "0.8")
    monkeypatch.setenv("ORENYL_SEMANTIC_DEDUP_THRESHOLD_CAREER", "0.95")

    first = semantic_dedup_threshold_for_domains(["health", "career"])
    second = semantic_dedup_threshold_for_domains(["career", "health"])

    assert first == 0.95
    assert second == 0.95
