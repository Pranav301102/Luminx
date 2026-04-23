# Person 2 - Phase 2 Roadmap: Dynamic Mesh Integration

**Timeline**: Week 3-5 (3 weeks)  
**Owner**: Shefali (Person 2)  
**Status**: Phase 1 Complete, Ready for Phase 2 planning

---

## Phase 2 Goals

1. **Autonomous node join** - New nodes discover and join cluster without manual wiring
2. **Dynamic allocation** - Nodes join/leave without stopping generation
3. **Layer assignment visibility** - UI shows topology changes in near real-time
4. **Bootstrap patterns** - mDNS for LAN, seed peers for WAN

---

## Phase 2 Deliverables

### 1. mDNS Local Discovery ✅ Architected (Phase 2 implementation)

**What to build**:
- Implement `MDNSRegistry` in `lumina_sprint1/discovery.py`
- Register tracker and nodes as mDNS services
- Implement `PeerDiscovery._discover_mdns()` and `_query_mdns()`
- Add zeroconf dependency

**Service names** (RFC 6762):
- `_lumina-tracker._tcp.local.`
- `_lumina-head._tcp.local.`
- `_lumina-tail._tcp.local.`

**Expected outcome**:
```bash
# On LAN, nodes auto-discover tracker
./node-a.py  # Finds tracker via mDNS
./node-b.py  # Finds tracker via mDNS
```

**Effort**: 2-3 days

---

### 2. Seed Peer Bootstrap (WAN)

**What to build**:
- Implement seed peer list propagation
- Add `register_seed()` pattern for bootstrap
- Update tracker to advertise seed peers in `/nodes/list`

**Config environment**:
```bash
LUMINA_SEED_PEERS="10.0.0.1:8003,10.0.0.2:8003"
LUMINA_DISCOVERY_MODE="mdns"
```

**Expected flow**:
```
Node joins cluster:
1. Start with seed peers from env
2. Try mDNS discovery
3. Fall back to seed peers if mDNS fails
4. Register with tracker
5. Join assignments
```

**Effort**: 1 day

---

### 3. Redis Backend for Tracker State

**What to build**:
- Replace in-memory tracker state with Redis
- Store node registry, assignments, request traces
- Implement Redis connection pool and reconnection logic
- Add backup mode (in-memory fallback on Redis failure)

**Schema** (Redis keys):
```
tracker:nodes:{node_id}          -> NodeState
tracker:assignments:current      -> AssignmentState
tracker:requests:{request_id}    -> RequestTrace
tracker:requests:recent          -> Sorted set of recent request IDs
```

**Expected outcome**:
- Tracker persistence across restarts
- Multi-tracker setup possible (Phase 3)
- Request history survives failures

**Effort**: 2-3 days

---

### 4. WebSocket Real-time Updates

**What to build**:
- Replace polling with WebSocket for assignment updates
- Implement push-based updates to frontend
- Add subscription model: `subscribe('/assignments/current')`

**Benefits**:
- Reduce latency from 5s to 100ms
- Lower CPU usage (no polling)
- Real-time cluster topology on dashboard

**Effort**: 1-2 days

---

### 5. Latency & Throughput Metrics

**What to build**:
- Measure per-node latency (inference time)
- Track throughput (tokens/sec)
- Update node scoring policy with real metrics

**Flow**:
1. Node A measures tail latency: `T_tail = tail_response_time`
2. Node B reports tail latency in response
3. Tracker aggregates metrics per node
4. Next `/assignment` uses updated split based on actual performance

**Metrics schema**:
```python
@dataclass
class NodeMetrics:
    latency_p95_ms: float  # 95th percentile inference time
    throughput_tps: float  # Tokens per second
    last_updated: float
```

**Expected outcome**:
- Dynamic assignment adapts to actual performance
- Bottleneck node gets smaller split

**Effort**: 1-2 days

---

### 6. Heartbeat Leases & Renewal

**What to build**:
- Implement lease semantics: each node gets `lease_duration_sec`
- Node must call `/lease/renew` before lease expires
- Automatic reassignment on lease expiry
- Lease duration from assignment response

**Response format**:
```json
{
  "split_layer": 2,
  "total_layers": 4,
  "version": 1,
  "lease_duration_sec": 60
}
```

**Benefits**:
- Faster failure detection (60s vs 30s default)
- Node can request longer lease if loaded

**Effort**: 1 day

---

## Phase 2 Implementation Timeline

| Week | Task | Owner | Days |
|------|------|-------|------|
| 3    | mDNS discovery + seed peers | Person 2 | 3 |
| 3    | Redis backend | Person 2 | 3 |
| 4    | WebSocket real-time | Person 2 | 2 |
| 4    | Latency/throughput metrics | Person 1 + 2 | 2 |
| 4    | Lease renewal & tests | Person 2 | 1 |
| 5    | Integration testing | All | 3 |
| 5    | Multi-node deployment | Person 4 | 2 |

---

## Phase 2 Success Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| Node join time | Time to first inference | <5s |
| Assignment convergence | Time to optimal split | <1s |
| Failure detection | Time to detect stale node | 30-60s |
| Real-time latency | Dashboard update latency | <100ms |
| Metrics accuracy | Throughput prediction error | ±10% |
| Persistence | Recovery after restart | 100% |

---

## Architecture Changes for Phase 2

### Current (Phase 1)
```
Client -> Tracker (in-memory) -> Nodes
         ^
         Single tracker, no discovery
```

### Phase 2
```
Client -> Tracker (Redis-backed) -> Nodes
              ^
         mDNS + seed peers
         
Bootstrap:
1. Node reads SEED_PEERS from env
2. Queries mDNS for tracker
3. Falls back to SEED_PEERS if needed
4. Registers with tracker
5. Gets assignment from tracker
```

### Phase 3 (DHT)
```
Client -> Tracker (DHT) -> Nodes
              ^
         DHT bootstrap (decentralized)
```

---

## Dependencies to Add

### For mDNS (Phase 2):
```
zeroconf>=0.130.0
```

### For Redis (Phase 2):
```
redis>=5.0.0
aioredis>=2.0.0  # or async-only redis client
```

### For WebSocket (Phase 2):
```
websockets>=12.0
```

Update `requirements.txt`:
```
# Phase 1
fastapi==0.116.0
uvicorn[standard]==0.35.0
transformers==4.54.1
torch==2.8.0
requests==2.32.4
pydantic==2.11.7
pydantic-settings==2.10.1
pytest==8.4.1

# Phase 2+
zeroconf>=0.130.0
redis>=5.0.0
websockets>=12.0
```

---

## Backward Compatibility

**Phase 2 must maintain Phase 1 compatibility**:
- ✅ All Phase 1 endpoints remain unchanged
- ✅ Old DTOs still work (add new optional fields)
- ✅ Static discovery mode still works
- ✅ In-memory fallback if Redis unavailable

**Example**:
```python
# Phase 1: In-memory only
tracker = AssignmentManager(...)

# Phase 2: Redis-backed
tracker = RedisAssignmentManager(redis_url='redis://localhost')

# If Redis fails, auto-fallback to in-memory
tracker = RedisAssignmentManager(
    redis_url='redis://localhost',
    fallback_to_memory=True
)
```

---

## Testing Strategy for Phase 2

### Unit Tests
- Test mDNS registration/discovery
- Test seed peer fallback logic
- Test Redis persistence and recovery
- Test lease renewal semantics
- Test metrics aggregation

### Integration Tests
- 3-node cluster: 1 tracker, 2 inference nodes
- Node join while generation in-flight
- Node failure during generation
- Tracker restart with Redis recovery
- WebSocket connection drops and recovery

### Load Tests
- 100 nodes joining cluster
- 1000 requests/sec throughput
- Latency percentiles (p50, p95, p99)

---

## Deployment for Phase 2

### Local Testing
```bash
docker-compose -f docker-compose.phase2.yml up
```

### Staging (Multi-machine)
```bash
# Machine 1: Tracker + Redis
docker run -d -p 6379:6379 redis

# Machine 2: Node A
NODE_B_URL=http://machine3:8002 \
TRACKER_URL=http://machine1:8003 \
LUMINA_DISCOVERY_MODE=static \
uvicorn node_a:app --host 0.0.0.0 --port 8001

# Machine 3: Node B
TRACKER_URL=http://machine1:8003 \
LUMINA_DISCOVERY_MODE=static \
uvicorn node_b:app --host 0.0.0.0 --port 8002
```

---

## Known Issues & Mitigations

### Issue: mDNS name collisions on shared network
**Mitigation**: Add environment variable for mDNS prefix
```
LUMINA_MDNS_PREFIX=company-lumina
# Services: _company-lumina-tracker._tcp.local.
```

### Issue: Redis becomes bottleneck
**Mitigation**: Implement read replicas and cache warming
- Tracker caches assignment in memory
- Update cache on version change only

### Issue: Network partition isolates tracker
**Mitigation**: Implement quorum-based tracking (Phase 3)
- Require N/2+1 nodes to agree on assignment

---

## References for Phase 2

- **mDNS/Avahi**: https://github.com/jstasiak/python-zeroconf
- **Redis for Python**: https://github.com/redis/redis-py
- **WebSocket server**: https://github.com/python-websockets/websockets
- **Hivemind DHT**: https://github.com/learning-at-home/hivemind
- **Petals Distributed Training**: https://github.com/bigscience-workshop/petals

---

## Approval Checklist for Phase 2 Start

- [ ] Person 1: Core inference stable and tested
- [ ] Person 3: Frontend ClusterPage ready for WebSocket integration
- [ ] Person 4: Docker infrastructure prepared for multi-machine
- [ ] Person 2: Phase 1 deliverables documented and tested
- [ ] All: Phase 1 end-to-end demo successful

---

**Phase 1 Status**: ✅ COMPLETE  
**Phase 2 Status**: 🚀 READY TO START

Next steps:
1. Review Phase 2 roadmap with team
2. Assign Phase 2 sprints (Week 3-5)
3. Set up Redis and mDNS infrastructure
4. Begin mDNS discovery implementation
