# Lumina Tracker API - Person 2 Control Plane

## Overview

The Tracker service is the distributed systems control plane for Lumina. It manages:
- Node registration and heartbeat lifecycle
- Dynamic layer assignment based on VRAM and node capacity
- Request tracing and monitoring
- Failure detection and automatic reassignment

**Base URL**: `http://localhost:8003` (local) or `http://tracker:8003` (Docker)

---

## Contract A: Node Management APIs

### POST /register
Register a node with the cluster and receive initial assignment.

**Request**:
```json
{
  "node_id": "node-a",
  "role": "head|tail",
  "vram_gb": 8.0,
  "max_layers": 3,
  "total_layers": 4
}
```

**Response**:
```json
{
  "split_layer": 2,
  "total_layers": 4,
  "version": 1
}
```

**Notes**:
- Called on node startup
- `split_layer` is the boundary: head handles [0, split_layer), tail handles [split_layer, total_layers)
- Version increments when assignment changes

---

### POST /heartbeat
Send heartbeat to keep node alive and receive current assignment.

**Request**:
```json
{
  "node_id": "node-a"
}
```

**Response**:
```json
{
  "split_layer": 2,
  "total_layers": 4,
  "version": 1
}
```

**Notes**:
- Nodes must heartbeat at least every `heartbeat_timeout_sec` (default: 30s)
- If heartbeat stops, node becomes stale and is removed from assignments
- New assignment triggers version increment

---

### POST /lease/renew
Renew lease for a node (alternative to heartbeat, more explicit for Phase 2+).

**Request**:
```json
{
  "node_id": "node-a"
}
```

**Response**:
```json
{
  "split_layer": 2,
  "total_layers": 4,
  "version": 1
}
```

---

### GET /nodes/list
List all nodes with metadata and live status.

**Response**:
```json
{
  "nodes": [
    {
      "node_id": "node-a",
      "role": "head",
      "vram": 8.0,
      "max_layers": 3,
      "status": "active|stale",
      "latency_ms": 0.0,
      "throughput_tps": 0.0,
      "last_heartbeat": "2s ago"
    }
  ]
}
```

**Notes**:
- `status` is "active" if last heartbeat within timeout, else "stale"
- `latency_ms` and `throughput_tps` are placeholders for Phase 2+ metrics

---

## Contract B: Assignment APIs

### GET /assignment
Get current global assignment (legacy).

**Response**:
```json
{
  "split_layer": 2,
  "total_layers": 4,
  "version": 1
}
```

---

### GET /assignments/current
List current layer assignments for all active nodes.

**Response**:
```json
{
  "assignments": [
    {
      "node_id": "node-a",
      "layer_start": 0,
      "layer_end": 2
    },
    {
      "node_id": "node-b",
      "layer_start": 2,
      "layer_end": 4
    }
  ]
}
```

**Notes**:
- Each assignment is `[layer_start, layer_end)` (half-open interval)
- Head node handles layers [0, split_layer)
- Tail node handles layers [split_layer, total_layers)
- Stale nodes are excluded from assignments

---

## Contract C: Request Tracing APIs

### POST /requests/start
Start tracing a request (called by Node A on /generate).

**Request**:
```json
{
  "request_id": "req-uuid-123",
  "prompt": "Lumina is",
  "assigned_nodes": ["node-a", "node-b"]
}
```

**Response**:
```json
{
  "request_id": "req-uuid-123",
  "status": "started"
}
```

**Notes**:
- Tracker records prompt, assignment, and start time
- Used for latency breakdown and failure diagnostics

---

### POST /requests/update
Update request status during execution.

**Request**:
```json
{
  "request_id": "req-uuid-123",
  "status": "pending|in_progress|completed|failed",
  "error": ""
}
```

**Response**:
```json
{
  "request_id": "req-uuid-123",
  "status": "in_progress"
}
```

**Notes**:
- Call with `status: "in_progress"` when request starts
- Call with `status: "completed"` when request finishes
- Include error message if `status: "failed"`

---

### GET /requests/trace/{request_id}
Retrieve latency trace for a specific request.

**Response**:
```json
{
  "trace": {
    "request_id": "req-uuid-123",
    "prompt": "Lumina is",
    "status": "completed",
    "duration_ms": 250.5,
    "assigned_nodes": ["node-a", "node-b"],
    "error": ""
  }
}
```

---

### GET /requests/traces?limit=100
List recent request traces (for TracePage UI).

**Response**:
```json
{
  "traces": [
    {
      "request_id": "req-uuid-123",
      "prompt": "Lumina is...",
      "status": "completed",
      "duration_ms": 250.5,
      "assigned_nodes": ["node-a", "node-b"],
      "error": ""
    }
  ]
}
```

**Notes**:
- Kept in memory only (max 1000 recent traces)
- Prompt truncated to first 50 chars for display
- Error truncated to first 100 chars

---

## Failure Handling

### Node Stale Detection
- Tracker detects stale nodes via monotonic clock
- Node is stale if `now - last_heartbeat > heartbeat_timeout_sec` (default: 30s)
- Stale nodes are excluded from new assignments
- In-flight requests on stale nodes may timeout (Person 1 and 2 coordination)

### Automatic Reassignment
- When a node becomes stale, remaining nodes rebalance dynamically
- New split_layer computed by VRAM ratio and capacity constraints
- Version increments to signal clients of assignment change

### Example Failure Scenario
1. Node B becomes stale (no heartbeat for 30s)
2. Next heartbeat from Node A triggers `_rebalance()`
3. Assignment reverts to `fallback_split_layer` or single-node mode
4. Version increments
5. Node A's next `/heartbeat` response has new version
6. Node A queries `/assignments/current` and gets updated assignment
7. In-flight requests on Node B may fail; Node A handles retry/fallback

---

## Configuration

### Environment Variables
- `SPLIT_LAYER` (default: 2): Initial fallback split point
- `HEARTBEAT_TIMEOUT_SEC` (default: 30): Stale node threshold
- `MODEL_NAME` (default: sshleifer/tiny-gpt2): Model for load estimation

### Docker Compose
```yaml
tracker:
  environment:
    - SPLIT_LAYER=2
    - HEARTBEAT_TIMEOUT_SEC=30
```

---

## Node Scoring Policy (Phase 1 Placeholder)

**Current** (VRAM ratio only):
```
target_split = (head_vram / total_vram) * total_layers
```

**Constraints**:
- `target >= min_for_tail` (tail must have enough capacity)
- `target <= head_capacity` (head can't exceed its max layers)
- `1 <= target <= total_layers - 1` (valid range)

**Phase 2+** will add:
- Latency per layer (measured from inference)
- Throughput per node (tokens/sec)
- Age of node / network proximity

---

## Integration Checklist

### For Person 1 (Inference)
- [ ] Call `POST /register` on Node A and Node B startup
- [ ] Call `POST /heartbeat` periodically (e.g., once per request)
- [ ] Call `POST /requests/start` when request begins
- [ ] Call `POST /requests/update` to track request status
- [ ] Poll `GET /assignment` or listen for version changes to detect reassignment

### For Person 3 (Frontend)
- [ ] Fetch `GET /nodes/list` every 3-5s for cluster view
- [ ] Fetch `GET /assignments/current` every 3-5s for layer assignments
- [ ] Fetch `GET /requests/traces` for trace timeline
- [ ] Display node status as "active" or "stale" based on `last_heartbeat`

### For Person 4 (Deployment)
- [ ] Ensure tracker health check passes before starting nodes
- [ ] Monitor tracker logs for stale node detection
- [ ] Set `HEARTBEAT_TIMEOUT_SEC` based on network latency (3x max RTT)
- [ ] Ensure tracker persistence or state recovery on restart (Phase 2+)

---

## Schema Reference

See `lumina_sprint1/schemas.py` for Pydantic models:
- `NodeRegisterRequest`, `NodeHeartbeatRequest`
- `NodeInfo`, `NodeListResponse`
- `AssignmentEntry`, `AssignmentsResponse`
- `RequestStartRequest`, `RequestUpdateRequest`
- `RequestTrace`, `RequestTraceResponse`, `RequestTracesResponse`

---

## Testing

Run tracker unit tests:
```bash
pytest tests/test_tracker_core.py -v
```

Test endpoints live:
```bash
uvicorn tracker:app --reload --port 8003
# In another terminal:
curl -X POST http://localhost:8003/register -H 'Content-Type: application/json' \
  -d '{"node_id":"node-a","role":"head","vram_gb":8.0,"max_layers":3,"total_layers":4}'
```

---

## Next Steps (Phase 2+)

- [ ] Add Redis backend for persistent tracker state
- [ ] Add mDNS discovery for dynamic node join in LAN
- [ ] Add gRPC transport for lower-latency control plane
- [ ] Add metrics export (Prometheus) for monitoring
- [ ] Add request idempotency and lease semantics
- [ ] Implement DHT-based rebalancing (Hivemind pattern)
