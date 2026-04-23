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
    def __init__(self, total_layers: int, fallback_split_layer: int, heartbeat_timeout_sec: int = 30):
        if total_layers < 2:
            raise ValueError('total_layers must be >= 2')
        self.total_layers = total_layers
        self.fallback_split_layer = max(1, min(fallback_split_layer, total_layers - 1))
        self.heartbeat_timeout_sec = heartbeat_timeout_sec
        self.nodes: dict[str, NodeState] = {}
        self.current_split_layer = self.fallback_split_layer
        self.version = 1
        self.request_traces: dict[str, RequestTrace] = {}  # request_id -> RequestTrace
        self.request_max_history = 1000  # Keep last N traces

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
    ) -> int:
        if total_layers is not None and total_layers >= 2 and total_layers != self.total_layers:
            self.total_layers = int(total_layers)
            self.fallback_split_layer = max(1, min(self.fallback_split_layer, self.total_layers - 1))
            self.current_split_layer = max(1, min(self.current_split_layer, self.total_layers - 1))

        self.nodes[node_id] = NodeState(
            node_id=node_id,
            role=role,
            vram_gb=max(0.1, float(vram_gb)),
            max_layers=max(1, int(max_layers)),
            last_seen=monotonic(),
        )
        self._rebalance()
        return self.current_split_layer

    def heartbeat(self, node_id: str) -> int:
        node = self.nodes.get(node_id)
        if node is not None:
            node.last_seen = monotonic()
        self._rebalance()
        return self.current_split_layer

    def lease_renewal(self, node_id: str) -> int:
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
        split, total, _ = self.assignment()
        assignments: list[dict] = []
        head = self._active_node_for_role('head')
        tail = self._active_node_for_role('tail')

        if head is not None:
            assignments.append(
                {
                    'node_id': head.node_id,
                    'layer_start': 0,
                    'layer_end': split,
                }
            )

        if tail is not None:
            assignments.append(
                {
                    'node_id': tail.node_id,
                    'layer_start': split,
                    'layer_end': total,
                }
            )

        return assignments

    def detect_stale_nodes(self) -> list[str]:
        """Return list of stale node IDs that have not heartbeat within timeout."""
        now = monotonic()
        stale = [
            node.node_id
            for node in self.nodes.values()
            if (now - node.last_seen) > self.heartbeat_timeout_sec
        ]
        return stale

    def cleanup_stale_nodes(self) -> bool:
        """Remove stale nodes and trigger rebalance. Returns True if any node was removed."""
        stale = self.detect_stale_nodes()
        if not stale:
            return False

        for node_id in stale:
            del self.nodes[node_id]

        self._rebalance()
        return True

    def start_request(self, request_id: str, prompt: str, assigned_nodes: list[str]) -> None:
        """Record the start of a request with assigned nodes."""
        self.request_traces[request_id] = RequestTrace(
            request_id=request_id,
            prompt=prompt,
            status='pending',
            started_at=monotonic(),
            assigned_nodes=assigned_nodes,
        )
        # Keep memory bounded
        if len(self.request_traces) > self.request_max_history:
            oldest_id = min(
                self.request_traces.keys(),
                key=lambda rid: self.request_traces[rid].started_at,
            )
            del self.request_traces[oldest_id]

    def update_request(self, request_id: str, status: str, error: str = '') -> None:
        """Update request status (in_progress, completed, failed)."""
        if request_id in self.request_traces:
            trace = self.request_traces[request_id]
            trace.status = status
            if error:
                trace.error = error
            if status in ['completed', 'failed']:
                trace.completed_at = monotonic()

    def get_request_trace(self, request_id: str) -> dict | None:
        """Return trace for a specific request."""
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
        """Return recent request traces."""
        traces = list(self.request_traces.values())
        traces.sort(key=lambda t: t.started_at, reverse=True)
        return [
            {
                'request_id': t.request_id,
                'prompt': t.prompt[:50],  # Truncate for display
                'status': t.status,
                'duration_ms': t.duration_ms(),
                'assigned_nodes': t.assigned_nodes,
                'error': t.error[:100] if t.error else '',
            }
            for t in traces[:limit]
        ]

    def _rebalance(self) -> None:
        head = self._active_node_for_role('head')
        tail = self._active_node_for_role('tail')

        if head is None or tail is None:
            target = self.fallback_split_layer
        else:
            total_vram = head.vram_gb + tail.vram_gb
            if total_vram <= 0:
                target = self.fallback_split_layer
            else:
                raw = int(round((head.vram_gb / total_vram) * self.total_layers))
                target = max(1, min(raw, self.total_layers - 1))

            head_cap = max(1, min(head.max_layers, self.total_layers - 1))
            min_for_tail = max(1, self.total_layers - max(1, min(tail.max_layers, self.total_layers - 1)))
            target = max(min_for_tail, min(target, head_cap))

        if target != self.current_split_layer:
            self.current_split_layer = target
            self.version += 1

    def assignment(self) -> tuple[int, int, int]:
        self._rebalance()
        return self.current_split_layer, self.total_layers, self.version
