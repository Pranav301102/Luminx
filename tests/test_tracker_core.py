from lumina_sprint1.tracker_core import AssignmentManager


def test_assignment_uses_vram_ratio_and_updates_version() -> None:
    manager = AssignmentManager(total_layers=12, fallback_split_layer=6, heartbeat_timeout_sec=30)

    split1 = manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=11, total_layers=12)
    split2 = manager.upsert_node('node-b', 'tail', vram_gb=4.0, max_layers=11, total_layers=12)

    assert split1 == 6
    assert split2 == 8

    # Tail becomes stronger, so split should move earlier and version should bump.
    manager.upsert_node('node-b', 'tail', vram_gb=12.0, max_layers=11, total_layers=12)
    split, _, version = manager.assignment()

    assert split == 5
    assert version >= 3


def test_assignment_falls_back_when_nodes_are_stale() -> None:
    manager = AssignmentManager(total_layers=10, fallback_split_layer=4, heartbeat_timeout_sec=1)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=9, total_layers=10)
    manager.upsert_node('node-b', 'tail', vram_gb=8.0, max_layers=9, total_layers=10)

    manager.nodes['node-a'].last_seen -= 100
    manager.nodes['node-b'].last_seen -= 100

    split, _, _ = manager.assignment()
    assert split == 4


def test_assignment_respects_capacity_limits() -> None:
    manager = AssignmentManager(total_layers=16, fallback_split_layer=8, heartbeat_timeout_sec=30)

    manager.upsert_node('node-a', 'head', vram_gb=20.0, max_layers=4, total_layers=16)
    manager.upsert_node('node-b', 'tail', vram_gb=1.0, max_layers=15, total_layers=16)

    split, _, _ = manager.assignment()
    assert split == 4
