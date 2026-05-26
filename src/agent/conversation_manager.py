"""
瀵硅瘽绠＄悊鍣?璐熻矗澶氳疆瀵硅瘽鐘舵€佺鐞?"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Message:
    """瀵硅瘽娑堟伅"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """浼氳瘽涓婁笅鏂?""
    session_id: str
    user_id: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    current_intent: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)  # 妲戒綅淇℃伅
    turn_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


class ConversationManager:
    """
    瀵硅瘽绠＄悊鍣?    - 绠＄悊澶氳疆瀵硅瘽鐘舵€?    - 缁存姢涓婁笅鏂囦俊鎭?    - 鏀寔瀵硅瘽鍘嗗彶
    """

    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self.sessions: Dict[str, ConversationContext] = {}

    def get_or_create_session(self, session_id: str) -> ConversationContext:
        """鑾峰彇鎴栧垱寤轰細璇?""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationContext(session_id=session_id)
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str, metadata: Dict = None) -> Message:
        """娣诲姞娑堟伅鍒颁細璇?""
        session = self.get_or_create_session(session_id)

        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )

        session.messages.append(message)
        session.turn_count += 1
        session.last_updated = datetime.now()

        # 淇濇寔鍘嗗彶闀垮害
        if len(session.messages) > self.max_history:
            session.messages = session.messages[-self.max_history:]

        return message

    def get_history(self, session_id: str, last_n: int = None) -> List[Message]:
        """鑾峰彇瀵硅瘽鍘嗗彶"""
        session = self.get_or_create_session(session_id)
        if last_n:
            return session.messages[-last_n:]
        return session.messages

    def update_context(self, session_id: str, **kwargs):
        """鏇存柊浼氳瘽涓婁笅鏂?""
        session = self.get_or_create_session(session_id)

        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

    def get_context_summary(self, session_id: str) -> Dict:
        """鑾峰彇涓婁笅鏂囨憳瑕?""
        session = self.get_or_create_session(session_id)

        return {
            "session_id": session_id,
            "turn_count": session.turn_count,
            "current_intent": session.current_intent,
            "slots": session.slots,
            "message_count": len(session.messages)
        }

    def clear_session(self, session_id: str):
        """娓呴櫎浼氳瘽"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def export_session(self, session_id: str) -> str:
        """瀵煎嚭浼氳瘽涓?JSON"""
        session = self.get_or_create_session(session_id)
        return json.dumps({
            "session_id": session.session_id,
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
                for m in session.messages
            ],
            "context": self.get_context_summary(session_id)
        }, ensure_ascii=False, indent=2)

    def build_context_for_llm(self, session_id: str, system_prompt: str = "") -> str:
        """鏋勫缓鍙戦€佺粰 LLM 鐨勪笂涓嬫枃瀛楃涓?""
        session = self.get_or_create_session(session_id)

        context_parts = []

        if system_prompt:
            context_parts.append(f"绯荤粺鎻愮ず: {system_prompt}")

        if session.current_intent:
            context_parts.append(f"褰撳墠鎰忓浘: {session.current_intent}")

        if session.slots:
            context_parts.append(f"宸叉敹闆嗕俊鎭? {json.dumps(session.slots, ensure_ascii=False)}")

        # 鏈€杩戝璇濆巻鍙?        history = self.get_history(session_id, last_n=10)
        if history:
            history_str = "\n".join([f"{m.role}: {m.content}" for m in history])
            context_parts.append(f"瀵硅瘽鍘嗗彶:\n{history_str}")

        return "\n\n".join(context_parts)