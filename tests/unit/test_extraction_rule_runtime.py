from orenyl.extraction_rule import ExtractionFact
from orenyl.extraction_runtime import NullExtractionRuntime


def test_extraction_fact_carries_confidence_and_model_id():
    fact = ExtractionFact(
        key="active_medications",
        value=["metformin"],
        confidence=0.92,
        model_id="gpt-test",
    )
    assert fact.confidence == 0.92
    assert fact.model_id == "gpt-test"


def test_null_extraction_runtime_returns_no_facts():
    runtime = NullExtractionRuntime()
    assert runtime.extract_facts({"type": "note", "payload": {"text": "hello"}}) == []
