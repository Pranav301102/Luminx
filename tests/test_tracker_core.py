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


def test_node_list_returns_node_metadata_and_status() -> None:
    manager = AssignmentManager(total_layers=12, fallback_split_layer=6, heartbeat_timeout_sec=30)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=11, total_layers=12)
    manager.upsert_node('node-b', 'tail', vram_gb=4.0, max_layers=11, total_layers=12)

    node_list = manager.node_list()
    assert any(node['node_id'] == 'node-a' and node['status'] == 'active' for node in node_list)
    assert any(node['node_id'] == 'node-b' and node['status'] == 'active' for node in node_list)
    assert len(node_list) == 2


def test_node_assignments_returns_head_and_tail_range() -> None:
    manager = AssignmentManager(total_layers=12, fallback_split_layer=6, heartbeat_timeout_sec=30)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=11, total_layers=12)
    manager.upsert_node('node-b', 'tail', vram_gb=4.0, max_layers=11, total_layers=12)

    assignments = manager.node_assignments()
    assert assignments[0]['node_id'] == 'node-a'
    assert assignments[0]['layer_start'] == 0
    assert assignments[0]['layer_end'] == 8
    assert assignments[1]['node_id'] == 'node-b'
    assert assignments[1]['layer_start'] == 8
    assert assignments[1]['layer_end'] == 12


def test_detect_stale_nodes_identifies_expired_nodes() -> None:
    manager = AssignmentManager(total_layers=10, fallback_split_layer=5, heartbeat_timeout_sec=1)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=9, total_layers=10)
    manager.upsert_node('node-b', 'tail', vram_gb=8.0, max_layers=9, total_layers=10)

    # Nodes are initially active
    stale = manager.detect_stale_nodes()
    assert len(stale) == 0

    # After timeout expires, both become stale
    manager.nodes['node-a'].last_seen -= 100
    manager.nodes['node-b'].last_seen -= 100

    stale = manager.detect_stale_nodes()
    assert set(stale) == {'node-a', 'node-b'}


def test_cleanup_stale_nodes_removes_and_rebalances() -> None:
    manager = AssignmentManager(total_layers=10, fallback_split_layer=5, heartbeat_timeout_sec=1)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=9, total_layers=10)
    manager.upsert_node('node-b', 'tail', vram_gb=8.0, max_layers=9, total_layers=10)

    # Mark node-b as stale
    manager.nodes['node-b'].last_seen -= 100

    # Cleanup should remove stale node
    cleaned = manager.cleanup_stale_nodes()
    assert cleaned is True
    assert 'node-b' not in manager.nodes
    assert len(manager.nodes) == 1

    # Assignment should now use fallback since tail is gone
    split, _, _ = manager.assignment()
    assert split == 5  # fallback value
