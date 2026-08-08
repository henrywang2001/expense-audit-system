"""
应用配置管理
使用Pydantic进行配置验证和管理
集成 DeepSeek LLM 和 千问 Embedding
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Expense Audit System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/expense_audit.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    DEEPSEEK_API_KEY: str
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    MODEL_NAME: str = "deepseek-v4-flash"
    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 4096
    DASHSCOPE_API_KEY: str
    DASHSCOPE_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    EMBEDDING_MODEL: str = "text-embedding-v1"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION: str = "expense_knowledge"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
