from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic


@dataclass
class NodeState:
    node_id: str
    role: str
    vram_gb: float
    max_layers: int
    last_seen: float


@dataclass
class RequestTrace:
    request_id: str
    prompt: str
    status: str  # pending, in_progress, completed, failed
    started_at: float
    completed_at: float = 0.0
    assigned_nodes: list[str] = field(default_factory=list)
    error: str = ''

    def duration_ms(self) -> float:
        end = self.completed_at if self.completed_at > 0 else monotonic()
        return (end - self.started_at) * 1000


class AssignmentManager:
    def __init__(
        self,
        total_layers: int,
        fallback_split_layer: int,
        fallback_split_layer_b: int | None = None,
        heartbeat_timeout_sec: int = 30,
    ):
        if total_layers < 3:
            raise ValueError('total_layers must be >= 3')
        self.total_layers = total_layers
        self.fallback_split_layer_a = max(1, min(fallback_split_layer, total_layers - 2))
        self.fallback_split_layer_b = max(
            self.fallback_split_layer_a + 1,
            min(
                fallback_split_layer_b if fallback_split_layer_b is not None else (total_layers * 2 // 3),
                total_layers - 1,
            ),
        )
        self.heartbeat_timeout_sec = heartbeat_timeout_sec
        self.nodes: dict[str, NodeState] = {}
        self.current_split_layer_a = self.fallback_split_layer_a
        self.current_split_layer_b = self.fallback_split_layer_b
        self.version = 1
        self.request_traces: dict[str, RequestTrace] = {}
        self.request_max_history = 1000

    def _node_status(self, node: NodeState) -> str:
        return 'active' if (monotonic() - node.last_seen) <= self.heartbeat_timeout_sec else 'stale'

    def _active_node_for_role(self, role: str) -> NodeState | None:
        now = monotonic()
        candidates = [
            node
            for node in self.nodes.values()
            if node.role == role and (now - node.last_seen) <= self.heartbeat_timeout_sec
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda n: n.last_seen, reverse=True)
        return candidates[0]

    def upsert_node(
        self,
        node_id: str,
        role: str,
        vram_gb: float,
        max_layers: int,
        total_layers: int | None = None,
    ) -> tuple[int, int]:
        if total_layers is not None and total_layers >= 3 and total_layers != self.total_layers:
            self.total_layers = int(total_layers)
            self.fallback_split_layer_a = max(1, min(self.fallback_split_layer_a, self.total_layers - 2))
            self.fallback_split_layer_b = max(
                self.fallback_split_layer_a + 1,
                min(self.fallback_split_layer_b, self.total_layers - 1),
            )

        self.nodes[node_id] = NodeState(
            node_id=node_id,
            role=role,
            vram_gb=max(0.1, float(vram_gb)),
            max_layers=max(1, int(max_layers)),
            last_seen=monotonic(),
        )
        self._rebalance()
        return self.current_split_layer_a, self.current_split_layer_b

    def heartbeat(self, node_id: str) -> tuple[int, int]:
        node = self.nodes.get(node_id)
        if node is not None:
            node.last_seen = monotonic()
        self._rebalance()
        return self.current_split_layer_a, self.current_split_layer_b

    def lease_renewal(self, node_id: str) -> tuple[int, int]:
        return self.heartbeat(node_id)

    def node_list(self) -> list[dict]:
        now = monotonic()
        return [
            {
                'node_id': node.node_id,
                'role': node.role,
                'vram': node.vram_gb,
                'max_layers': node.max_layers,
                'status': 'active' if (now - node.last_seen) <= self.heartbeat_timeout_sec else 'stale',
                'latency_ms': 0.0,
                'throughput_tps': 0.0,
                'last_heartbeat': f'{int(now - node.last_seen)}s ago',
            }
            for node in self.nodes.values()
        ]

    def node_assignments(self) -> list[dict]:
        split_a, split_b, total, _ = self.assignment()
        assignments: list[dict] = []
        head = self._active_node_for_role('head')
        mid = self._active_node_for_role('mid')
        tail = self._active_node_for_role('tail')

        if head is not None:
            assignments.append({'node_id': head.node_id, 'layer_start': 0, 'layer_end': split_a})
        if mid is not None:
            assignments.append({'node_id': mid.node_id, 'layer_start': split_a, 'layer_end': split_b})
        if tail is not None:
            assignments.append({'node_id': tail.node_id, 'layer_start': split_b, 'layer_end': total})

        return assignments

    def detect_stale_nodes(self) -> list[str]:
        now = monotonic()
        return [
            node.node_id
            for node in self.nodes.values()
            if (now - node.last_seen) > self.heartbeat_timeout_sec
        ]

    def cleanup_stale_nodes(self) -> bool:
        stale = self.detect_stale_nodes()
        if not stale:
            return False
        for node_id in stale:
            del self.nodes[node_id]
        self._rebalance()
        return True

    def start_request(self, request_id: str, prompt: str, assigned_nodes: list[str]) -> None:
        self.request_traces[request_id] = RequestTrace(
            request_id=request_id,
            prompt=prompt,
            status='pending',
            started_at=monotonic(),
            assigned_nodes=assigned_nodes,
        )
        if len(self.request_traces) > self.request_max_history:
            oldest_id = min(
                self.request_traces.keys(),
                key=lambda rid: self.request_traces[rid].started_at,
            )
            del self.request_traces[oldest_id]

    def update_request(self, request_id: str, status: str, error: str = '') -> None:
        if request_id in self.request_traces:
            trace = self.request_traces[request_id]
            trace.status = status
            if error:
                trace.error = error
            if status in ['completed', 'failed']:
                trace.completed_at = monotonic()

    def get_request_trace(self, request_id: str) -> dict | None:
        if request_id not in self.request_traces:
            return None
        trace = self.request_traces[request_id]
        return {
            'request_id': trace.request_id,
            'prompt': trace.prompt,
            'status': trace.status,
            'duration_ms': trace.duration_ms(),
            'assigned_nodes': trace.assigned_nodes,
            'error': trace.error,
        }

    def list_request_traces(self, limit: int = 100) -> list[dict]:
        traces = list(self.request_traces.values())
        traces.sort(key=lambda t: t.started_at, reverse=True)
        return [
            {
                'request_id': t.request_id,
                'prompt': t.prompt[:50],
                'status': t.status,
                'duration_ms': t.duration_ms(),
                'assigned_nodes': t.assigned_nodes,
                'error': t.error[:100] if t.error else '',
            }
            for t in traces[:limit]
        ]

    def _rebalance(self) -> None:
        head = self._active_node_for_role('head')
        mid = self._active_node_for_role('mid')
        tail = self._active_node_for_role('tail')

        if head is None or tail is None:
            # Not enough nodes registered — use fallback
            new_a = self.fallback_split_layer_a
            new_b = self.fallback_split_layer_b
        elif mid is None:
            # 2-node mode: head + tail only (no mid registered yet)
            total_vram = head.vram_gb + tail.vram_gb
            if total_vram > 0:
                raw = int(round((head.vram_gb / total_vram) * self.total_layers))
                split_a = max(1, min(raw, self.total_layers - 1))
            else:
                split_a = self.fallback_split_layer_a

            # Apply per-node capacity limits
            head_cap = max(1, min(head.max_layers, self.total_layers - 1))
            tail_min = max(1, self.total_layers - max(1, min(tail.max_layers, self.total_layers - 1)))
            split_a = max(tail_min, min(split_a, head_cap))

            new_a = split_a
            new_b = split_a  # mid and tail collapse to same boundary
        else:
            # 3-node mode: VRAM-proportional split
            total_vram = head.vram_gb + mid.vram_gb + tail.vram_gb
            if total_vram > 0:
                raw_a = int(round((head.vram_gb / total_vram) * self.total_layers))
                raw_b = int(round(((head.vram_gb + mid.vram_gb) / total_vram) * self.total_layers))
            else:
                raw_a = self.fallback_split_layer_a
                raw_b = self.fallback_split_layer_b

            new_a = max(1, min(raw_a, self.total_layers - 2))
            new_b = max(new_a + 1, min(raw_b, self.total_layers - 1))

        changed = (new_a != self.current_split_layer_a) or (new_b != self.current_split_layer_b)
        if changed:
            self.current_split_layer_a = new_a
            self.current_split_layer_b = new_b
            self.version += 1

    def assignment(self) -> tuple[int, int, int, int]:
        """Return (split_layer_a, split_layer_b, total_layers, version)."""
        self._rebalance()
        return self.current_split_layer_a, self.current_split_layer_b, self.total_layers, self.version
