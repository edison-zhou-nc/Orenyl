from lore.repositories.facts import FactMixin


def test_fact_mixin_has_fact_and_rule_registry_api():
    required = {
        "insert_fact",
        "get_current_facts",
        "get_current_facts_by_domain",
        "get_fact",
        "get_latest_version",
        "invalidate_fact",
        "get_facts_by_key",
        "get_facts_by_ids",
        "list_current_facts_by_rule_family",
        "update_fact_rule_version",
        "mark_facts_stale",
        "register_rule_version",
        "set_rule_version_active",
        "get_active_rule_versions",
    }
    assert required <= set(dir(FactMixin))
