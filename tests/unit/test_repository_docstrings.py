from orenyl.repositories.facts import FactMixin
from orenyl.repositories.lineage import LineageMixin


def test_repository_mixins_preserve_key_docstrings():
    assert (
        FactMixin.get_current_facts.__doc__
        == "Get all valid, non-invalidated facts (optionally filtered by key)."
    )
    assert (
        FactMixin.get_facts_by_key.__doc__
        == "Get all versions of facts for a key (including invalidated)."
    )
    assert (
        LineageMixin.get_downstream_facts.__doc__
        == "Recursively find downstream facts using a single SQL CTE."
    )
