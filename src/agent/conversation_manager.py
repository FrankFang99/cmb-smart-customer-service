"""
对话管理器
负责多轮对话状态管理
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Message:
    """对话消息"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """会话上下文"""
    session_id: str
    user_id: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    current_intent: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)  # 槽位信息
    turn_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


class ConversationManager:
    """
    对话管理器
    - 管理多轮对话状态
    - 维护上下文信息
    - 支持对话历史
    """

    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self.sessions: Dict[str, ConversationContext] = {}

    def get_or_create_session(self, session_id: str) -> ConversationContext:
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationContext(session_id=session_id)
        return self.sessions[session_id]

    def add_message(self, session_id: str, role: str, content: str, metadata: Dict = None) -> Message:
        """添加消息到会话"""
        session = self.get_or_create_session(session_id)

        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )

        session.messages.append(message)
        session.turn_count += 1
        session.last_updated = datetime.now()

        # 保持历史长度
        if len(session.messages) > self.max_history:
            session.messages = session.messages[-self.max_history:]

        return message

    def get_history(self, session_id: str, last_n: int = None) -> List[Message]:
        """获取对话历史"""
        session = self.get_or_create_session(session_id)
        if last_n:
            return session.messages[-last_n:]
        return session.messages

    def update_context(self, session_id: str, **kwargs):
        """更新会话上下文"""
        session = self.get_or_create_session(session_id)

        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

    def get_context_summary(self, session_id: str) -> Dict:
        """获取上下文摘要"""
        session = self.get_or_create_session(session_id)

        return {
            "session_id": session_id,
            "turn_count": session.turn_count,
            "current_intent": session.current_intent,
            "slots": session.slots,
            "message_count": len(session.messages)
        }

    def clear_session(self, session_id: str):
        """清除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def export_session(self, session_id: str) -> str:
        """导出会话为 JSON"""
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
        """构建发送给 LLM 的上下文字符串"""
        session = self.get_or_create_session(session_id)

        context_parts = []

        if system_prompt:
            context_parts.append(f"系统提示: {system_prompt}")

        if session.current_intent:
            context_parts.append(f"当前意图: {session.current_intent}")

        if session.slots:
            context_parts.append(f"已收集信息: {json.dumps(session.slots, ensure_ascii=False)}")

        # 最近对话历史
        history = self.get_history(session_id, last_n=10)
        if history:
            history_str = "\n".join([f"{m.role}: {m.content}" for m in history])
            context_parts.append(f"对话历史:\n{history_str}")

        return "\n\n".join(context_parts)