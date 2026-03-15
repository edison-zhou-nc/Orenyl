from lore.repositories.lineage import LineageMixin


def test_lineage_mixin_has_graph_api():
    required = {
        "insert_edge",
        "get_children",
        "get_parents",
        "get_parents_for_children",
        "get_downstream_facts",
        "delete_edges_for_item",
        "hard_delete_facts_by_source",
        "run_vacuum",
    }
    assert required <= set(dir(LineageMixin))
