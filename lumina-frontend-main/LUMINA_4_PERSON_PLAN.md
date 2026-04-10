# Lumina Deployment Roadmap - 4 Person Execution Plan

## Team Objective
Build Lumina as a distributed LLM inference system with clear ownership across core inference, distributed orchestration, frontend, and deployment.

## Team Roles and Ownership

### Person 1 - Core Inference Lead 
Owns model execution internals and performance-critical logic.

- Model loading and block partitioning.
- Forward-pass interception and token generation loop.
- Tensor payload contract and schema versioning.
- KV cache policy, batching policy, dtype strategy.
- Correctness tests for split inference outputs.
- Dynamic layer assignment and rebalance policy.

Deliverables:
- Stable inference handoff contract (schema v1).
- Multi-token generation across split nodes.
- Regression tests for deterministic prompts.

Out of scope:
- Discovery protocol implementation.
- Deployment infra and cluster operations.
- Frontend dashboard development.

### Person 2 - Distributed Systems Lead
Owns cluster control plane and distributed routing logic.

- Peer registration and node metadata lifecycle.
- Discovery system (LAN mDNS + WAN bootstrap).
- Heartbeat service and failure detection.
- DHT migration plan using Hivemind patterns.

Deliverables:
- Tracker service APIs: register, heartbeat, assign_layers, lease_renewal.
- Node scoring policy (VRAM, latency, throughput).
- Automatic reassignment on node loss.

Out of scope:
- Model internals.
- Frontend design decisions.
- CI/CD and infra provisioning.

### Person 3 - Frontend and Product UX Lead
Owns operational dashboard and user-facing inference UI.

- Prompt/chat UI for generation requests.
- Cluster topology and node health views.
- Request tracing and latency breakdown views.
- Real-time status updates from backend APIs.

Deliverables:
- Dashboard pages: Chat, Cluster, Health, Trace.
- API integration for streaming and non-streaming responses.
- Operator-focused UX for demos and debugging.

Out of scope:
- Inference kernel changes.
- Container and runtime infrastructure.

### Person 4 - Deployment and SRE Lead
Owns runtime reliability, multi-container deployment, and observability.

- Docker image strategy and Compose topology.
- Environment management and secret handling.
- Kubernetes manifests or Helm chart.
- Logging, metrics, health checks, alerting.
- CI/CD automation and release flow.

Deliverables:
- Reproducible local stack and staging stack.
- Monitoring stack and incident runbooks.
- Multi-node deploy scripts and rollback path.

Out of scope:
- Core transformer logic.
- Frontend feature ownership.

---

## Phased Plan

## Phase 1 - Static Pipeline PoC Hardening (Week 1-2)
Goal: reliable split inference across two nodes with clear API contracts.

Person 1:
- Finalize head/tail split flow and multi-token loop.
- Lock tensor serialization schema and tests.

Person 2:
- Build minimal tracker with static assignments.
- Introduce node registration endpoint.

Person 3:
- Build simple prompt UI + health view.

Person 4:
- Harden Docker Compose for repeatable local runs.
- Add basic healthcheck and restart policy.

Definition of Done:
- Prompt enters Node A, hidden states reach Node B, response returns consistently.
- Full stack starts with one command.
- Basic dashboard confirms live status.

## Phase 2 - Dynamic Mesh Integration (Week 3-5)
Goal: autonomous node join and dynamic allocation.

Person 1:
- Expose model capability metadata (layers supported, precision, max context).

Person 2:
- Add heartbeat leases, dynamic assignments, and rebalancing.
- Add Redis bootstrap path and mDNS local discovery path.
- Prepare Hivemind DHT migration adapter.

Person 3:
- Add cluster map with assignment visibility and heartbeat updates.

Person 4:
- Deploy distributed setup beyond single-machine Compose.
- Add environment and secrets templates for staging.

Definition of Done:
- New nodes join without manual wiring.
- Layer assignments adapt to changing capacity.
- UI reflects topology changes in near real-time.

## Phase 3 - Fault Tolerance and Self-Healing (Week 6-8)
Goal: maintain service continuity under node failure.

Person 1:
- Add safe pause/resume hooks for token generation.

Person 2:
- Implement failover protocol for in-flight requests.
- Enforce idempotency and request lease semantics.

Person 3:
- Build failure timeline and request recovery visibility.

Person 4:
- Add chaos tests and SLO-based alerts.
- Validate automated restart and rollback behavior.

Definition of Done:
- Node failure triggers reassignment and bounded recovery.
- In-flight requests either resume safely or fail with clear diagnostics.
- Incident details visible in logs and dashboard.

---

## API and Contract Boundaries

### Contract A - Inference Handoff (Person 1 <-> Person 2)
Required fields:
- request_id
- model_id
- layer_start
- layer_end
- hidden_state_payload
- attention_mask
- cache_state_ref
- schema_version

### Contract B - Control Plane API (Person 2 <-> Person 3)
Endpoints:
- nodes/list
- nodes/register
- nodes/heartbeat
- assignments/current
- requests/trace

### Contract C - Runtime Config (Person 1 and Person 2 <-> Person 4)
Config domains:
- model revision and storage path
- transport mode
- heartbeat interval and lease timeout
- bootstrap/discovery mode
- observability sink endpoints

---

## Milestones and Primary Owners

1. End-to-end local mesh demo
- Owner: Person 1
- Support: Person 2, Person 3, Person 4

2. Dynamic node join and rebalance
- Owner: Person 2
- Support: Person 1, Person 3, Person 4

3. Node failure recovery demo
- Owner: Person 2 and Person 4
- Support: Person 1, Person 3

4. Public demo and project report
- Owner: Person 3
- Support: all

---

## Success Metrics
- p95 end-to-end latency by prompt length bucket.
- Tokens/sec per node and cluster aggregate.
- Node join time and assignment convergence time.
- Recovery time after worker failure.
- In-flight request recovery success rate.
- Deployment reproducibility on clean hosts.

---

## Risks and Mitigations

1. Tensor shape/dtype mismatch across nodes.
- Owner: Person 1
- Mitigation: strict schema versioning + tensor validation tests.

2. Discovery instability across mixed LAN/WAN environments.
- Owner: Person 2
- Mitigation: dual-mode discovery with fallback seed peers.

3. Multi-container deployment complexity.
- Owner: Person 4
- Mitigation: progressive environments (local -> staging -> distributed).

4. Frontend blocked by changing backend contracts.
- Owner: Person 2 and Person 3
- Mitigation: frozen DTOs + mocked API fixtures.

5. Failover duplicates or corrupts in-flight generation.
- Owner: Person 1 and Person 2
- Mitigation: idempotency keys + resumable request state.

---

## References

### Distributed Inference and DHT
- Petals repository: https://github.com/bigscience-workshop/petals
- Petals site: https://petals.dev/
- Hivemind repository: https://github.com/learning-at-home/hivemind
- BloomBee repository: https://github.com/ai-decentralized/BloomBee

### Discovery and Topology
- Exo repository: https://github.com/exo-explore/exo
- mDNS overview (RFC 6762 context): https://en.wikipedia.org/wiki/Multicast_DNS

### P2P Network Patterns
- Hyperspace node repository: https://github.com/hyperspaceai/hyperspace-node
- libp2p docs: https://libp2p.io/

### Bootstrap Messaging and Transport
- Redis Pub/Sub semantics: https://redis.io/docs/latest/develop/pubsub/
- Redis PUBLISH command: https://redis.io/docs/latest/commands/publish/
- Redis SUBSCRIBE command: https://redis.io/docs/latest/commands/subscribe/
- gRPC introduction: https://grpc.io/docs/what-is-grpc/introduction/

---

## Suggested Weekly Cadence
- Monday: ownership sync + interface contract review.
- Wednesday: integration checkpoint and blocker resolution.
- Friday: demo slice and metrics review.

This rhythm keeps each owner autonomous while forcing early interface validation.
