from lore.repositories.events import EventMixin


def test_event_mixin_has_event_read_write_api():
    required = {
        "insert_event",
        "get_event",
        "find_event_by_content_hash",
        "get_active_events",
        "get_active_events_by_subject",
        "get_active_domains_by_subject",
        "get_recent_events_in_domains",
        "get_events_by_ids",
        "get_all_events",
        "get_active_events_by_domains",
        "get_events_by_domains",
        "count_events_by_domains",
        "list_events_page",
        "get_event_count",
        "get_latest_event_ts",
        "get_expired_events",
        "soft_delete_event",
        "hard_delete_event",
        "update_event_payload",
        "update_event_retention",
    }
    assert required <= set(dir(EventMixin))
