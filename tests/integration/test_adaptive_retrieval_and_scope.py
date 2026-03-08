from lore.context_pack import should_retrieve


def test_should_retrieve_skips_greetings_but_keeps_memory_queries():
    assert should_retrieve("hello there") is False
    assert should_retrieve("what do you remember about my health") is True

