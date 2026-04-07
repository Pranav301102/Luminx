from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    model_name: str = 'sshleifer/tiny-gpt2'
    split_layer: int = 2
    max_new_tokens: int = 20

    node_b_url: str = 'http://localhost:8002'


settings = Settings()
