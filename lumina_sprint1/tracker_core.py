from __future__ import annotations

from dataclasses import dataclass
from time import monotonic


@dataclass
class NodeState:
    node_id: str
    role: str
    vram_gb: float
    max_layers: int
    last_seen: float


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
