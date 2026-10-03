from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_DB = f"sqlite:///{PROJECT_ROOT / 'data' / 'aeris.db'}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aeris_env: str = "real"
    aeris_data_mode: str = "real_IMD"
    secret_key: str = "change-me-in-any-non-demo-environment"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "https://aeris-1-iy0y.onrender.com,http://localhost:3000"

    database_url: str = DEFAULT_SQLITE_DB
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    mlflow_tracking_uri: str = "http://localhost:5001"
    mlflow_experiment: str = "aeris-trust-engine"

    nwp_base_url: str = ""
    nwp_api_key: str = ""
    obs_base_url: str = ""
    obs_api_key: str = ""

    auth_disabled: bool = True
    default_role: str = "VIEWER"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Keep the supported persistence backends explicit and predictable."""
        if value.startswith("sqlite://") or value.startswith("mysql+pymysql://"):
            return value
        raise ValueError(
            "DATABASE_URL must use SQLite (sqlite:///) or MySQL "
            "(mysql+pymysql://)."
        )

    @property
    def database_backend(self) -> str:
        return "sqlite" if self.database_url.startswith("sqlite://") else "mysql"


@lru_cache
def get_settings() -> Settings:
    return Settings()
