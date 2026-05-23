from tools.unified_log_helper_correlator import build_dag


def test_build_dag_basic_lifecycle():
    events = [
        {
            "event_id": "evt1",
            "event_type": "helper.spawn",
            "timestamp": "2026-05-05 20:00:00.000000",
            "line_no": 1,
            "root_intent_id": "intent.test",
            "phase": "cache_cleanup",
            "pid": 1,
            "service_key": "svc",
            "lifecycle_state": "will_spawn",
        },
        {
            "event_id": "evt2",
            "event_type": "helper.spawn",
            "timestamp": "2026-05-05 20:00:00.100000",
            "line_no": 2,
            "root_intent_id": "intent.test",
            "phase": "cache_cleanup",
            "pid": 1,
            "service_key": "svc",
            "lifecycle_state": "xpcproxy_spawned",
        },
        {
            "event_id": "evt3",
            "event_type": "helper.exit",
            "timestamp": "2026-05-05 20:00:01.000000",
            "line_no": 3,
            "root_intent_id": "intent.test",
            "phase": "cache_cleanup",
            "pid": 1,
            "service_key": "svc",
            "lifecycle_state": "exited",
        },
    ]

    dag = build_dag(events)
    assert dag["summary"]["event_count"] == 3
    assert dag["summary"]["edge_type_counts"]["contains_phase"] == 1
    assert dag["summary"]["edge_type_counts"]["same_pid_next_event"] >= 2
    assert dag["summary"]["edge_type_counts"]["lifecycle_progression"] >= 2
