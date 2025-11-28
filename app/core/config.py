from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data.db"
    service_base_url: str
    integration_base_url: str = ""
    admin_username: str = ""
    admin_password: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()