from orenyl.db import Database
from orenyl.models import Fact


def test_db_has_embedding_tables_and_fact_confidence_fields():
    db = Database(":memory:")
    fact_cols = {row["name"] for row in db.conn.execute("PRAGMA table_info(facts)").fetchall()}
    assert "confidence" in fact_cols
    assert "model_id" in fact_cols

    db.conn.execute("SELECT * FROM event_embeddings LIMIT 1").fetchall()
    db.conn.execute("SELECT * FROM fact_embeddings LIMIT 1").fetchall()

    fact = Fact(
        id="fact:test:v1",
        key="test_key",
        value={"v": 1},
        rule_id="Rule@v1",
        confidence=0.85,
        model_id="test-model",
    )
    assert fact.confidence == 0.85
    assert fact.model_id == "test-model"
