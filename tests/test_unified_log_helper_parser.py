from tools.unified_log_helper_parser import parse_text


def test_parse_mdworker_spawn():
    text = "2026-05-05 20:40:14.174009 (user/501/com.apple.mdworker.shared.08000000-0600-0000-0000-000000000000) <Notice>: internal event: WILL_SPAWN, code = 0"
    events = parse_text(text)
    assert len(events) == 1
    assert events[0]["event_type"] == "helper.spawn"
    assert events[0]["phase"] == "spotlight_metadata_indexing"
    assert events[0]["policy_profile"] == "indexer.metadata_local.v1"


def test_parse_denied_pasteboard():
    text = "2026-05-05 20:42:00.415146 (gui/501 [100023]) <Warning>: denied lookup: name = com.apple.pasteboard.1, requestor = WebThumbnailExt[53926], error = 159: Sandbox restriction"
    events = parse_text(text)
    assert len(events) == 1
    assert events[0]["event_type"] == "capability.request"
    assert events[0]["capability"] == "pasteboard.read"
    assert events[0]["decision"] == "deny"
    assert events[0]["data_accessed"] is False
    assert events[0]["phase"] == "web_thumbnail_or_webkit_helper"


def test_parse_teardown_without_context():
    text = "2026-05-05 20:42:03.378197 <Error>: invalid client reply port -1"
    events = parse_text(text)
    assert len(events) == 1
    assert events[0]["event_type"] == "teardown.normalized"
    assert events[0]["normalized_class"] == "invalid_reply_endpoint_after_teardown"
