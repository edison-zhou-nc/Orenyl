"""Lazy accessors to server globals for extracted handler modules."""


def get_db():
    from ..server import db

    return db


def get_engine():
    from ..server import engine

    return engine


def get_pack_builder():
    from ..server import pack_builder

    return pack_builder
