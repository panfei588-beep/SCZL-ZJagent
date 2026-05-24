from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM (OpenAI compatible - Claude via proxy)
    openai_api_key: str = ""
    openai_base_url: str = ""

    # DashScope (Milvus embedding only)
    dashscope_api_key: str = ""

    milvus_host: str = "localhost"
    milvus_port: int = 19530

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "quality_diagnosis"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres123"

    mineru_backend: str = "pipeline"

    server_host: str = "0.0.0.0"
    server_port: int = 8000

    upload_dir: str = "./uploads"
    max_upload_size: int = 52428800

    # LangGraph Workflow
    confidence_threshold: float = 0.6
    data_retry_limit: int = 3
    rag_top_k: int = 5
    charts_dir: str = "./charts"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
