from lumina_sprint1.tracker_core import AssignmentManager


# ── 2-node tests (head + tail, no mid) ───────────────────────────────────────

def test_two_node_vram_ratio_and_version() -> None:
    manager = AssignmentManager(total_layers=12, fallback_split_layer=6, heartbeat_timeout_sec=30)

    split_a1, _ = manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=11, total_layers=12)
    split_a2, _ = manager.upsert_node('node-b', 'tail', vram_gb=4.0, max_layers=11, total_layers=12)

    assert split_a1 == 6   # only head registered: falls back
    assert split_a2 == 8   # head(8) + tail(4) → 8/12 * 12 = 8

    # Tail becomes stronger: split should move earlier
    manager.upsert_node('node-b', 'tail', vram_gb=12.0, max_layers=11, total_layers=12)
    split_a, _split_b, _total, version = manager.assignment()

    assert split_a == 5    # 8/20 * 12 ≈ 5
    assert version >= 3


def test_two_node_fallback_when_stale() -> None:
    manager = AssignmentManager(total_layers=10, fallback_split_layer=4, heartbeat_timeout_sec=1)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=9, total_layers=10)
    manager.upsert_node('node-b', 'tail', vram_gb=8.0, max_layers=9, total_layers=10)

    manager.nodes['node-a'].last_seen -= 100
    manager.nodes['node-b'].last_seen -= 100

    split_a, _split_b, _total, _version = manager.assignment()
    assert split_a == 4


def test_two_node_capacity_limits() -> None:
    manager = AssignmentManager(total_layers=16, fallback_split_layer=8, heartbeat_timeout_sec=30)
    manager.upsert_node('node-a', 'head', vram_gb=20.0, max_layers=4, total_layers=16)
    manager.upsert_node('node-b', 'tail', vram_gb=1.0, max_layers=15, total_layers=16)

    split_a, _split_b, _total, _version = manager.assignment()
    assert split_a == 4


def test_node_list_returns_metadata_and_status() -> None:
    manager = AssignmentManager(total_layers=12, fallback_split_layer=6, heartbeat_timeout_sec=30)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=11, total_layers=12)
    manager.upsert_node('node-b', 'tail', vram_gb=4.0, max_layers=11, total_layers=12)

    node_list = manager.node_list()
    assert any(n['node_id'] == 'node-a' and n['status'] == 'active' for n in node_list)
    assert any(n['node_id'] == 'node-b' and n['status'] == 'active' for n in node_list)
    assert len(node_list) == 2


def test_two_node_assignments() -> None:
    manager = AssignmentManager(total_layers=12, fallback_split_layer=6, heartbeat_timeout_sec=30)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=11, total_layers=12)
    manager.upsert_node('node-b', 'tail', vram_gb=4.0, max_layers=11, total_layers=12)

    assignments = manager.node_assignments()
    head_entry = next(a for a in assignments if a['node_id'] == 'node-a')
    tail_entry = next(a for a in assignments if a['node_id'] == 'node-b')

    assert head_entry['layer_start'] == 0
    assert head_entry['layer_end'] == 8
    assert tail_entry['layer_start'] == 8
    assert tail_entry['layer_end'] == 12


def test_detect_stale_nodes() -> None:
    manager = AssignmentManager(total_layers=10, fallback_split_layer=5, heartbeat_timeout_sec=1)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=9, total_layers=10)
    manager.upsert_node('node-b', 'tail', vram_gb=8.0, max_layers=9, total_layers=10)

    assert len(manager.detect_stale_nodes()) == 0

    manager.nodes['node-a'].last_seen -= 100
    manager.nodes['node-b'].last_seen -= 100

    assert set(manager.detect_stale_nodes()) == {'node-a', 'node-b'}


def test_cleanup_stale_nodes() -> None:
    manager = AssignmentManager(total_layers=10, fallback_split_layer=5, heartbeat_timeout_sec=1)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=9, total_layers=10)
    manager.upsert_node('node-b', 'tail', vram_gb=8.0, max_layers=9, total_layers=10)

    manager.nodes['node-b'].last_seen -= 100

    assert manager.cleanup_stale_nodes() is True
    assert 'node-b' not in manager.nodes

    split_a, _split_b, _total, _version = manager.assignment()
    assert split_a == 5  # fallback


# ── 3-node tests (head + mid + tail) ─────────────────────────────────────────

def test_three_node_equal_vram_splits_evenly() -> None:
    manager = AssignmentManager(total_layers=30, fallback_split_layer=10, heartbeat_timeout_sec=30)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=29, total_layers=30)
    manager.upsert_node('node-b', 'mid',  vram_gb=8.0, max_layers=29, total_layers=30)
    manager.upsert_node('node-c', 'tail', vram_gb=8.0, max_layers=29, total_layers=30)

    split_a, split_b, total, _version = manager.assignment()
    assert split_a == 10   # 8/24 * 30 = 10
    assert split_b == 20   # (8+8)/24 * 30 = 20
    assert total == 30


def test_three_node_vram_proportional_split() -> None:
    # head:mid:tail = 1:2:1 → splits at ~7, ~22 for 30 layers
    manager = AssignmentManager(total_layers=30, fallback_split_layer=10, heartbeat_timeout_sec=30)
    manager.upsert_node('node-a', 'head', vram_gb=4.0, max_layers=29, total_layers=30)
    manager.upsert_node('node-b', 'mid',  vram_gb=8.0, max_layers=29, total_layers=30)
    manager.upsert_node('node-c', 'tail', vram_gb=4.0, max_layers=29, total_layers=30)

    split_a, split_b, _total, _version = manager.assignment()
    # head gets 4/16 * 30 = 7.5 → 8
    # head+mid gets (4+8)/16 * 30 = 22.5 → 22 or 23
    assert split_a == 8
    assert split_b in (22, 23)


def test_three_node_assignments() -> None:
    manager = AssignmentManager(total_layers=30, fallback_split_layer=10, heartbeat_timeout_sec=30)
    manager.upsert_node('node-a', 'head', vram_gb=8.0, max_layers=29, total_layers=30)
    manager.upsert_node('node-b', 'mid',  vram_gb=8.0, max_layers=29, total_layers=30)
    manager.upsert_node('node-c', 'tail', vram_gb=8.0, max_layers=29, total_layers=30)

    assignments = manager.node_assignments()
    assert len(assignments) == 3

    head_e = next(a for a in assignments if a['node_id'] == 'node-a')
    mid_e  = next(a for a in assignments if a['node_id'] == 'node-b')
    tail_e = next(a for a in assignments if a['node_id'] == 'node-c')

    assert head_e['layer_start'] == 0
    assert head_e['layer_end'] == mid_e['layer_start']
    assert mid_e['layer_end'] == tail_e['layer_start']
    assert tail_e['layer_end'] == 30
