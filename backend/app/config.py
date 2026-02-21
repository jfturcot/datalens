from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    litellm_api_url: str = "https://litellm-production-f079.up.railway.app/"
    litellm_api_key: str = ""
    litellm_model: str = "claude-sonnet-4-5"

    # PostgreSQL
    postgres_user: str = "datalens"
    postgres_password: str = "change-me-in-production"
    postgres_db: str = "datalens"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # MinIO
    minio_root_user: str = "datalens"
    minio_root_password: str = "change-me-in-production"
    minio_endpoint: str = "minio:9000"
    minio_bucket: str = "uploads"
    minio_use_ssl: bool = False

    # App
    app_env: str = "development"
    session_secret: str = "change-me-in-production"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
