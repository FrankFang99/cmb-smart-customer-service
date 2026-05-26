"""
FastAPI 接口
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid

from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings


# 初始化 FastAPI
app = FastAPI(
    title="招商银行智能客服 API",
    description="AI 智能客服后端接口",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Agent
agent = CustomerServiceAgent(settings)

# 存储会话（生产环境用 Redis）
sessions = {}


# ===== 请求/响应模型 =====
class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str
    answer: str
    intent: str
    confidence: float
    tool_used: Optional[str] = None
    sources: List[str] = []
    timestamp: str


class SessionInfoResponse(BaseModel):
    """会话信息响应"""
    session_id: str
    turn_count: int
    current_intent: Optional[str]
    message_count: int


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str


# ===== API 路由 =====

@app.get("/", tags=["Health"])
async def root():
    """根路径"""
    return {"message": "招商银行智能客服 API", "version": "1.0.0"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """健康检查"""
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    聊天接口

    - **message**: 用户消息
    - **session_id**: 会话ID（可选，不提供则自动创建）
    - **user_id**: 用户ID（可选）
    """
    try:
        # 生成或使用 session_id
        session_id = request.session_id or str(uuid.uuid4())

        # 调用 Agent
        response = agent.chat(request.message, session_id)

        return ChatResponse(
            session_id=session_id,
            answer=response["answer"],
            intent=response["intent"],
            confidence=response["confidence"],
            tool_used=response.get("tool_used"),
            sources=response.get("sources", []),
            timestamp=response.get("timestamp", "")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务错误: {str(e)}")


@app.get("/session/{session_id}", response_model=SessionInfoResponse, tags=["Session"])
async def get_session_info(session_id: str):
    """
    获取会话信息

    - **session_id**: 会话ID
    """
    try:
        info = agent.get_session_info(session_id)
        return SessionInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"会话不存在: {str(e)}")


@app.delete("/session/{session_id}", tags=["Session"])
async def delete_session(session_id: str):
    """
    删除会话

    - **session_id**: 会话ID
    """
    # 这里可以实现会话删除逻辑
    return {"message": f"会话 {session_id} 已清除"}


@app.get("/intents", tags=["System"])
async def list_intents():
    """
    获取支持的意图列表

    用于前端展示意图选项
    """
    from src.components.intent_recognizer import IntentType

    return {
        "intents": [
            {"value": intent.value, "label": intent.name.replace("_", " ").title()}
            for intent in IntentType
        ]
    }


@app.get("/tools", tags=["System"])
async def list_tools():
    """
    获取可用的工具列表

    用于展示系统能力
    """
    from src.agent.tools import BANKING_TOOLS

    return {
        "tools": list(BANKING_TOOLS.keys())
    }


# ===== 启动信息 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)