from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    model_name: str = 'sshleifer/tiny-gpt2'
    split_layer: int = 2
    max_new_tokens: int = 20

    node_b_url: str = 'http://localhost:8002'
    tracker_url: str = 'http://localhost:8003'

    enable_dynamic_split: bool = True
    node_a_id: str = 'node-a'
    node_b_id: str = 'node-b'

    heartbeat_timeout_sec: int = 30

    # Phase 2+: Peer discovery configuration
    discovery_mode: str = 'static'  # static, mdns, dht
    seed_peers: str = ''  # Comma-separated host:port list


settings = Settings()
