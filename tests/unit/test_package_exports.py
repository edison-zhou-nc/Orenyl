from orenyl import handlers, repositories


def test_repositories_export_base_and_concrete_mixins() -> None:
    assert repositories.__all__ == [
        "BaseMixin",
        "AuditMixin",
        "ComplianceMixin",
        "EmbeddingMixin",
        "EventMixin",
        "FactMixin",
        "FederationMixin",
        "LineageMixin",
    ]


def test_handlers_export_modules_for_extraction_surface() -> None:
    assert handlers.__all__ == [
        "_common",
        "_deps",
        "compliance",
        "core",
        "operations",
        "tooling",
    ]
