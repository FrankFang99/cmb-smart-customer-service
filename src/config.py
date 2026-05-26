"""
项目配置文件
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # API Keys
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"

    # 模型配置
    llm_model: str = "deepseek-chat"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # 意图识别配置
    rule_confidence_threshold: float = 0.9
    model_confidence_threshold: float = 0.7
    llm_confidence_threshold: float = 0.5

    # RAG 配置
    top_k: int = 5
    retrieval_score_threshold: float = 0.5

    # 应用配置
    app_name: str = "招商银行智能客服"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()