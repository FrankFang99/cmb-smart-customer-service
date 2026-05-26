"""
椤圭洰閰嶇疆鏂囦欢
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """搴旂敤閰嶇疆"""

    # API Keys
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"

    # 妯″瀷閰嶇疆
    llm_model: str = "deepseek-chat"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # 鎰忓浘璇嗗埆閰嶇疆
    rule_confidence_threshold: float = 0.9
    model_confidence_threshold: float = 0.7
    llm_confidence_threshold: float = 0.5

    # RAG 閰嶇疆
    top_k: int = 5
    retrieval_score_threshold: float = 0.5

    # 搴旂敤閰嶇疆
    app_name: str = "鎷涘晢閾惰鏅鸿兘瀹㈡湇"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()