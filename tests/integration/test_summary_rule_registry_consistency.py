from lore.rules import ALL_RULES, DerivationRule
from lore.summary_rule import DomainSummaryRule


def test_summary_rule_is_canonical_derivation_rule():
    assert issubclass(DomainSummaryRule, DerivationRule)
    assert any(r.output_key == "domain_summary" for r in ALL_RULES)
