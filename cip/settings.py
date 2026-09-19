from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CIP_", extra="ignore")
    database_url: str = "sqlite:///./cip.db"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    mlflow_tracking_uri: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    feature_version: str = "rfm-behavior-affinity-v1"
    recommendation_version: str = "hybrid-v1"
    top_k: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()

