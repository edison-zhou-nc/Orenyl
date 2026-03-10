from lore.config import semantic_dedup_threshold_for_domains


def test_health_domain_threshold_override(monkeypatch):
    monkeypatch.setenv("LORE_SEMANTIC_DEDUP_THRESHOLD_DEFAULT", "0.92")
    monkeypatch.setenv("LORE_SEMANTIC_DEDUP_THRESHOLD_HEALTH", "0.97")
    threshold = semantic_dedup_threshold_for_domains(["health"])
    assert threshold == 0.97


def test_domain_threshold_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("LORE_SEMANTIC_DEDUP_THRESHOLD_DEFAULT", "0.91")
    threshold = semantic_dedup_threshold_for_domains(["career"])
    assert threshold == 0.91
