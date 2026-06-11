"""
测试 5: 对话管理器 (多轮状态)
"""
import pytest
from datetime import datetime
from src.agent.conversation_manager import ConversationManager, ConversationContext, Message


class TestConversationManager:
    """对话管理器测试"""

    def test_create_session(self):
        """创建会话"""
        mgr = ConversationManager()
        sess = mgr.get_or_create_session("s1")
        assert sess.session_id == "s1"
        assert sess.turn_count == 0
        assert len(sess.messages) == 0

    def test_get_existing_session_returns_same(self):
        """相同 session_id 返回同一对象"""
        mgr = ConversationManager()
        s1 = mgr.get_or_create_session("abc")
        s2 = mgr.get_or_create_session("abc")
        assert s1 is s2

    def test_add_message(self):
        """添加消息"""
        mgr = ConversationManager()
        msg = mgr.add_message("s1", "user", "你好")
        assert msg.role == "user"
        assert msg.content == "你好"
        assert isinstance(msg.timestamp, datetime)

    def test_turn_count_increments(self):
        """turn_count 自动递增"""
        mgr = ConversationManager()
        mgr.add_message("s1", "user", "你好")
        mgr.add_message("s1", "assistant", "您好!")
        mgr.add_message("s1", "user", "查余额")
        sess = mgr.get_or_create_session("s1")
        assert sess.turn_count == 3
        assert len(sess.messages) == 3

    def test_max_history_truncation(self):
        """超过 max_history 自动截断"""
        mgr = ConversationManager(max_history=3)
        for i in range(5):
            mgr.add_message("s1", "user", f"msg{i}")
        sess = mgr.get_or_create_session("s1")
        assert len(sess.messages) == 3  # 只留最近 3 条
        # 应该是 msg2, msg3, msg4
        assert sess.messages[0].content == "msg2"
        assert sess.messages[-1].content == "msg4"

    def test_get_history_last_n(self):
        """获取最近 n 条"""
        mgr = ConversationManager()
        for i in range(5):
            mgr.add_message("s1", "user", f"msg{i}")
        history = mgr.get_history("s1", last_n=2)
        assert len(history) == 2
        assert history[0].content == "msg3"
        assert history[1].content == "msg4"

    def test_update_context(self):
        """更新上下文"""
        mgr = ConversationManager()
        mgr.add_message("s1", "user", "查余额")
        mgr.update_context("s1", current_intent="info_acc_balance",
                            slots={"card": "6225"})
        sess = mgr.get_or_create_session("s1")
        assert sess.current_intent == "info_acc_balance"
        assert sess.slots["card"] == "6225"

    def test_context_summary(self):
        """上下文摘要"""
        mgr = ConversationManager()
        mgr.add_message("s1", "user", "你好")
        mgr.add_message("s1", "assistant", "您好")
        mgr.update_context("s1", current_intent="sys_greeting")
        summary = mgr.get_context_summary("s1")
        assert summary["turn_count"] == 2
        assert summary["current_intent"] == "sys_greeting"
        assert summary["message_count"] == 2

    def test_export_session_json(self):
        """导出会话为 JSON"""
        import json
        mgr = ConversationManager()
        mgr.add_message("s1", "user", "你好")
        mgr.add_message("s1", "assistant", "您好")
        exported = mgr.export_session("s1")
        data = json.loads(exported)
        assert data["session_id"] == "s1"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"

    def test_build_context_for_llm(self):
        """构建 LLM 上下文"""
        mgr = ConversationManager()
        mgr.add_message("s1", "user", "查余额")
        mgr.add_message("s1", "assistant", "请登录App查询")
        mgr.update_context("s1", current_intent="info_acc_balance",
                            slots={"user_id": "u123"})
        ctx = mgr.build_context_for_llm("s1", system_prompt="你是银行客服")
        assert "你是银行客服" in ctx
        assert "info_acc_balance" in ctx
        assert "u123" in ctx
        assert "查余额" in ctx
        assert "请登录App查询" in ctx

    def test_clear_session(self):
        """清除会话"""
        mgr = ConversationManager()
        mgr.add_message("s1", "user", "x")
        assert "s1" in mgr.sessions
        mgr.clear_session("s1")
        assert "s1" not in mgr.sessions
