"""
Lumina Peer Discovery Module - Phase 2 Foundation

This module provides the foundation for peer discovery in Phase 2:
- Seed bootstrap pattern (static peer list)
- mDNS discovery template (RFC 6762)
- DHT-based discovery placeholder (Hivemind pattern for Phase 3)

Phase 1: Static configuration only (single tracker address)
Phase 2: Add mDNS auto-discovery + seed fallback
Phase 3: Add DHT for decentralized discovery
"""

from dataclasses import dataclass
from typing import Optional
import socket


@dataclass
class PeerInfo:
    """Peer node information for discovery."""
    node_id: str
    addr: str
    port: int
    role: str  # 'head', 'tail', 'tracker'
    discovered_at: float = 0.0

    @property
    def url(self) -> str:
        return f"http://{self.addr}:{self.port}"


class DiscoveryMode:
    """Supported discovery modes."""
    STATIC = "static"  # Phase 1: hardcoded peers
    MDNS = "mdns"  # Phase 2: mDNS broadcast discovery
    DHT = "dht"  # Phase 3: Decentralized hash table


class PeerDiscovery:
    """
    Peer discovery manager supporting multiple modes.

    Phase 1 Usage:
        discovery = PeerDiscovery(mode='static')
        tracker = discovery.resolve_tracker(fallback='http://localhost:8003')

    Phase 2 Usage (planned):
        discovery = PeerDiscovery(mode='mdns', seed_peers=['10.0.0.1:8003'])
        tracker = discovery.resolve_tracker()  # Auto-discover tracker
    """

    def __init__(
        self,
        mode: str = DiscoveryMode.STATIC,
        seed_peers: Optional[list[str]] = None,
        mdns_timeout_sec: int = 5,
    ):
        """
        Initialize peer discovery.

        Args:
            mode: Discovery mode (static, mdns, dht)
            seed_peers: List of 'host:port' strings for bootstrap
            mdns_timeout_sec: Timeout for mDNS queries (Phase 2)
        """
        self.mode = mode
        self.seed_peers = seed_peers or []
        self.mdns_timeout_sec = mdns_timeout_sec
        self.peer_cache: dict[str, PeerInfo] = {}

    def resolve_tracker(self, fallback: Optional[str] = None) -> str:
        """
        Resolve tracker URL via discovery mode.

        Args:
            fallback: Fallback tracker URL if discovery fails

        Returns:
            Tracker URL (e.g., 'http://localhost:8003')

        Phase 1: Uses fallback only
        Phase 2: Try mDNS then fallback
        """
        if self.mode == DiscoveryMode.STATIC:
            return fallback or "http://localhost:8003"

        if self.mode == DiscoveryMode.MDNS:
            # Phase 2: Try mDNS discovery
            peer = self._discover_mdns("tracker")
            if peer:
                return peer.url
            # Fall back to seed peers
            if self.seed_peers:
                return f"http://{self.seed_peers[0]}"
            return fallback or "http://localhost:8003"

        if self.mode == DiscoveryMode.DHT:
            # Phase 3: DHT-based discovery (not implemented)
            raise NotImplementedError("DHT discovery in Phase 3")

        return fallback or "http://localhost:8003"

    def resolve_peers(self, role: str) -> list[str]:
        """
        Resolve peer URLs by role.

        Args:
            role: 'head', 'tail', or 'tracker'

        Returns:
            List of peer URLs

        Phase 1: Empty (all static in config)
        Phase 2: Discover via mDNS
        """
        if self.mode == DiscoveryMode.STATIC:
            return []

        if self.mode == DiscoveryMode.MDNS:
            # Phase 2: Query mDNS for all peers of given role
            # peers = self._query_mdns(role)
            # return [p.url for p in peers]
            return []

        return []

    def _discover_mdns(self, service_name: str) -> Optional[PeerInfo]:
        """
        Discover service via mDNS (Phase 2 placeholder).

        Service naming convention:
            _lumina-tracker._tcp.local.
            _lumina-head._tcp.local.
            _lumina-tail._tcp.local.

        Returns:
            First discovered peer or None
        """
        # Phase 2: Implement using zeroconf library
        # from zeroconf import ServiceBrowser, Zeroconf
        # zeroconf = Zeroconf()
        # browser = ServiceBrowser(zeroconf, f"_{service_name}._tcp.local.", listener)
        # ... collect results
        # zeroconf.close()
        return None

    def _query_mdns(self, service_name: str, timeout_sec: int = 5) -> list[PeerInfo]:
        """Query mDNS for all instances of a service (Phase 2 placeholder)."""
        # Phase 2: Implement using zeroconf
        return []

    def register_seed(self, host: str, port: int) -> None:
        """
        Register a seed peer for bootstrap.

        Used in Phase 2+ when joining a cluster:
            discovery.register_seed('10.0.0.1', 8003)
            tracker = discovery.resolve_tracker()
        """
        self.seed_peers.append(f"{host}:{port}")

    def __repr__(self) -> str:
        return (
            f"PeerDiscovery(mode={self.mode}, "
            f"seeds={len(self.seed_peers)}, "
            f"cached={len(self.peer_cache)})"
        )


class BootstrapConfig:
    """
    Bootstrap configuration for multi-node clusters.

    Phase 1: Single tracker, all nodes hardcoded
    Phase 2: Seed peers + mDNS discovery
    Phase 3: Full DHT bootstrap
    """

    def __init__(self, tracker_url: str = "http://localhost:8003"):
        """
        Initialize bootstrap config.

        Args:
            tracker_url: Primary tracker URL

        Environment override:
            LUMINA_TRACKER_URL - tracker address
            LUMINA_DISCOVERY_MODE - discovery mode (static, mdns, dht)
            LUMINA_SEED_PEERS - comma-separated seed peer list
        """
        self.tracker_url = tracker_url
        self.discovery = PeerDiscovery(mode=DiscoveryMode.STATIC)

    def get_tracker_url(self) -> str:
        """Get resolved tracker URL."""
        return self.discovery.resolve_tracker(fallback=self.tracker_url)

    @classmethod
    def from_env(cls) -> "BootstrapConfig":
        """
        Load bootstrap config from environment variables.

        Environment Variables:
            LUMINA_TRACKER_URL - tracker URL (default: http://localhost:8003)
            LUMINA_DISCOVERY_MODE - discovery mode (default: static)
            LUMINA_SEED_PEERS - comma-separated seeds (e.g., "10.0.0.1:8003,10.0.0.2:8003")
        """
        import os
        tracker_url = os.getenv("LUMINA_TRACKER_URL", "http://localhost:8003")
        mode = os.getenv("LUMINA_DISCOVERY_MODE", DiscoveryMode.STATIC)
        seed_peers_str = os.getenv("LUMINA_SEED_PEERS", "")

        config = cls(tracker_url)
        seed_peers = [s.strip() for s in seed_peers_str.split(",") if s.strip()]

        config.discovery = PeerDiscovery(mode=mode, seed_peers=seed_peers)
        return config


# Phase 2 Placeholder: mDNS Service Registration
class MDNSRegistry:
    """
    Register node as mDNS service (Phase 2 placeholder).

    Usage (Phase 2):
        registry = MDNSRegistry()
        registry.register_as_tracker("lumina-tracker", 8003)
        # ... service runs
        registry.shutdown()
    """

    def register_as_tracker(self, name: str, port: int) -> None:
        """Register as tracker service on mDNS."""
        # Phase 2: Use zeroconf to register
        # ServiceInfo(
        #     "_lumina-tracker._tcp.local.",
        #     f"{name}._lumina-tracker._tcp.local.",
        #     port=port,
        #     server=f"{hostname}.local."
        # )
        pass

    def register_as_node(self, node_id: str, role: str, port: int) -> None:
        """Register as inference node on mDNS."""
        # Phase 2: Register as _lumina-{role}._tcp.local.
        pass

    def shutdown(self) -> None:
        """Unregister from mDNS."""
        pass
