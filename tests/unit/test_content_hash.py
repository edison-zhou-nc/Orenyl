from orenyl.content_hash import compute_content_hash


def test_content_hash_normalizes_whitespace_and_case():
    assert compute_content_hash("  Hello   World ") == compute_content_hash("hello world")
