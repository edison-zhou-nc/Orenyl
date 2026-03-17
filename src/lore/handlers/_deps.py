"""Lazy accessors to server's module-level singletons for extracted handlers.

These accessors give handlers access to server's module-level singletons.
Handlers are not designed for standalone use outside the server context.
"""


def get_db():
    from ..server import db

    return db


def get_engine():
    from ..server import engine

    return engine


def get_pack_builder():
    from ..server import pack_builder

    return pack_builder


def get_embedding_provider():
    from ..server import _get_embedding_provider

    return _get_embedding_provider()


def get_compliance_service():
    from ..server import _get_compliance_service

    return _get_compliance_service()


def get_consent_service():
    from ..server import _get_consent_service

    return _get_consent_service()


def get_dr_service():
    from ..server import _get_dr_service

    return _get_dr_service()


def get_transport_mode():
    from ..server import get_transport_mode as _get_transport_mode

    return _get_transport_mode()


def get_max_context_pack_limit():
    from ..server import MAX_CONTEXT_PACK_LIMIT

    return MAX_CONTEXT_PACK_LIMIT


def get_max_list_events_limit():
    from ..server import MAX_LIST_EVENTS_LIMIT

    return MAX_LIST_EVENTS_LIMIT
