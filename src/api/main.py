"""
FastAPI 鎺ュ彛
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid

from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings


# 鍒濆鍖?FastAPI
app = FastAPI(
    title="鎷涘晢閾惰鏅鸿兘瀹㈡湇 API",
    description="AI 鏅鸿兘瀹㈡湇鍚庣鎺ュ彛",
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

# 鍒濆鍖?Agent
agent = CustomerServiceAgent(settings)

# 瀛樺偍浼氳瘽锛堢敓浜х幆澧冪敤 Redis锛?sessions = {}


# ===== 璇锋眰/鍝嶅簲妯″瀷 =====
class ChatRequest(BaseModel):
    """鑱婂ぉ璇锋眰"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    """鑱婂ぉ鍝嶅簲"""
    session_id: str
    answer: str
    intent: str
    confidence: float
    tool_used: Optional[str] = None
    sources: List[str] = []
    timestamp: str


class SessionInfoResponse(BaseModel):
    """浼氳瘽淇℃伅鍝嶅簲"""
    session_id: str
    turn_count: int
    current_intent: Optional[str]
    message_count: int


class HealthResponse(BaseModel):
    """鍋ュ悍妫€鏌ュ搷搴?""
    status: str
    version: str


# ===== API 璺敱 =====

@app.get("/", tags=["Health"])
async def root():
    """鏍硅矾寰?""
    return {"message": "鎷涘晢閾惰鏅鸿兘瀹㈡湇 API", "version": "1.0.0"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """鍋ュ悍妫€鏌?""
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    鑱婂ぉ鎺ュ彛

    - **message**: 鐢ㄦ埛娑堟伅
    - **session_id**: 浼氳瘽ID锛堝彲閫夛紝涓嶆彁渚涘垯鑷姩鍒涘缓锛?    - **user_id**: 鐢ㄦ埛ID锛堝彲閫夛級
    """
    try:
        # 鐢熸垚鎴栦娇鐢?session_id
        session_id = request.session_id or str(uuid.uuid4())

        # 璋冪敤 Agent
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
        raise HTTPException(status_code=500, detail=f"鏈嶅姟閿欒: {str(e)}")


@app.get("/session/{session_id}", response_model=SessionInfoResponse, tags=["Session"])
async def get_session_info(session_id: str):
    """
    鑾峰彇浼氳瘽淇℃伅

    - **session_id**: 浼氳瘽ID
    """
    try:
        info = agent.get_session_info(session_id)
        return SessionInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"浼氳瘽涓嶅瓨鍦? {str(e)}")


@app.delete("/session/{session_id}", tags=["Session"])
async def delete_session(session_id: str):
    """
    鍒犻櫎浼氳瘽

    - **session_id**: 浼氳瘽ID
    """
    # 杩欓噷鍙互瀹炵幇浼氳瘽鍒犻櫎閫昏緫
    return {"message": f"浼氳瘽 {session_id} 宸叉竻闄?}


@app.get("/intents", tags=["System"])
async def list_intents():
    """
    鑾峰彇鏀寔鐨勬剰鍥惧垪琛?
    鐢ㄤ簬鍓嶇灞曠ず鎰忓浘閫夐」
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
    鑾峰彇鍙敤鐨勫伐鍏峰垪琛?
    鐢ㄤ簬灞曠ず绯荤粺鑳藉姏
    """
    from src.agent.tools import BANKING_TOOLS

    return {
        "tools": list(BANKING_TOOLS.keys())
    }


# ===== 鍚姩淇℃伅 =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)