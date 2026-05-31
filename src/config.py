"""
项目配置文件
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # MiniMax API (优先)
    minimax_api_key: str = ""
    minimax_base_url: str = "https://agent.minimaxi.com/mavis/api/v1/llm/v1"
    
    # DeepSeek API (备用)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # 模型配置
    llm_model: str = "MiniMax-M2.7"
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

    def get_active_api_key(self) -> tuple:
        """获取当前可用的API配置"""
        if self.minimax_api_key and self.minimax_api_key != "sk-xxx":
            return self.minimax_api_key, self.minimax_base_url, "MiniMax"
        elif self.deepseek_api_key:
            return self.deepseek_api_key, self.deepseek_base_url, "DeepSeek"
        else:
            return None, None, None


settings = Settings()