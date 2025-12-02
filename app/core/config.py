from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///data.db"
    service_base_url: str

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()