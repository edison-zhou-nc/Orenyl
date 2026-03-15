from lore.repositories.compliance import ComplianceMixin


def test_compliance_mixin_has_subject_and_consent_api():
    required = {
        "insert_tombstone",
        "get_tombstones",
        "insert_consent_record",
        "latest_consent_status",
        "withdrawn_subject_ids",
        "list_consent_purposes",
        "create_subject_request",
        "has_agent_permission",
        "has_delegation_grant",
        "insert_dr_snapshot",
        "get_dr_snapshot",
    }
    assert required <= set(dir(ComplianceMixin))
