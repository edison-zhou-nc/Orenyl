from lore import context_pack as context_pack_module
from scripts.run_eval import run_phase1_precision_eval


class _SemanticTestProvider:
    provider_id = "semantic-test"
    dim = 3

    def embed_text(self, text: str) -> list[float]:
        lowered = (text or "").lower()
        if any(token in lowered for token in ("pharma", "metformin", "active_medications")):
            return [1.0, 0.0, 0.0]
        if any(token in lowered for token in ("permission", "admin", "current_role")):
            return [0.0, 1.0, 0.0]
        if any(token in lowered for token in ("meal", "vegan", "diet_preference")):
            return [0.0, 0.0, 1.0]
        return [0.0, 0.0, 0.0]


class _ZeroProvider:
    provider_id = "zero-test"
    dim = 3

    def embed_text(self, text: str) -> list[float]:
        return [0.0, 0.0, 0.0]


def _vector_only_ranker(**kwargs):
    vector_order = kwargs.get("vector_order") or []
    return [
        {"id": item_id, "score": float(len(vector_order) - idx)}
        for idx, item_id in enumerate(vector_order)
    ]


def test_phase1_vector_signal_improves_precision_on_tiebreaker_corpus(monkeypatch):
    corpus = "scenarios/phase1_vector_tiebreaker_corpus.json"
    monkeypatch.setattr(context_pack_module, "rank_items", _vector_only_ranker)
    monkeypatch.setattr(
        context_pack_module, "_get_embedding_provider", lambda: _SemanticTestProvider()
    )
    with_vector = run_phase1_precision_eval(corpus_path=corpus, top_k=1)

    monkeypatch.setattr(context_pack_module, "_get_embedding_provider", lambda: _ZeroProvider())
    without_vector = run_phase1_precision_eval(corpus_path=corpus, top_k=1)

    assert with_vector >= 0.9
    assert with_vector > without_vector
