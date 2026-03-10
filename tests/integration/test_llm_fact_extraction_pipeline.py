from lore.db import Database
from lore.lineage import LineageEngine
from lore.models import Event
from lore.extraction_rule import ExtractionFact


class _FakeExtractionRuntime:
    def extract_facts(self, event: dict) -> list[ExtractionFact]:
        return [
            ExtractionFact(
                key="medication_mentioned",
                value={"name": "metformin"},
                confidence=0.87,
                model_id="fake-llm-v1",
                rule_id="LLMExtractionRule@v1",
            )
        ]


def test_lineage_engine_persists_extracted_fact_with_confidence_and_model_id():
    db = Database(":memory:")
    engine = LineageEngine(db, extraction_runtime=_FakeExtractionRuntime())

    event = Event(
        id="event:test:extract",
        type="note",
        payload={"text": "I started metformin today"},
        domains=["health"],
    )
    db.insert_event(event)
    created_ids = engine.derive_facts_for_event(db.get_event(event.id))

    extracted_id = next(fact_id for fact_id in created_ids if "medication_mentioned" in fact_id)
    extracted = db.get_fact(extracted_id)
    assert extracted is not None
    assert extracted["confidence"] == 0.87
    assert extracted["model_id"] == "fake-llm-v1"
