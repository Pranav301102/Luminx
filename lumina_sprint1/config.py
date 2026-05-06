from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    model_name: str = 'microsoft/Phi-4-mini-instruct'
    max_new_tokens: int = 20

    # Layer split boundaries (32 total layers for Phi-4 Mini)
    # Node A runs [0, split_layer_a)
    # Node B runs [split_layer_a, split_layer_b)
    # Node C runs [split_layer_b, total_layers)
    split_layer_a: int = 10
    split_layer_b: int = 21
    # Kept for tracker backward-compat (= split_layer_a in 2-node fallback)
    split_layer: int = 10

    node_b_url: str = 'http://localhost:8002'
    node_c_url: str = 'http://localhost:8004'
    tracker_url: str = 'http://localhost:8003'

    enable_dynamic_split: bool = True
    node_a_id: str = 'node-a'
    node_b_id: str = 'node-b'
    node_c_id: str = 'node-c'

    heartbeat_timeout_sec: int = 30

    # Phase 2+: Peer discovery configuration
    discovery_mode: str = 'static'  # static, mdns, dht
    seed_peers: str = ''  # Comma-separated host:port list


settings = Settings()
