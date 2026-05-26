"""
Streamlit 聊天界面
"""
import streamlit as st
from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings
import uuid


# 页面配置
st.set_page_config(
    page_title="招商银行智能客服",
    page_icon="🏦",
    layout="centered"
)

# 初始化 Agent
@st.cache_resource
def init_agent():
    return CustomerServiceAgent(settings)

agent = init_agent()

# 会话管理
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = True


# 标题
st.title("🏦 招商银行智能客服")
st.markdown("您好！我是小招智能客服，有什么可以帮您？")

# 侧边栏 - 功能介绍
with st.sidebar:
    st.header("📌 功能说明")
    st.markdown("""
    **支持的服务：**
    - 账户余额查询
    - 信用卡账单查询
    - 网点地址查询
    - 理财产品咨询
    - 转账操作指引
    - 卡片挂失服务
    - 转人工服务

    **使用提示：**
    - 输入您的问题，小招会尽力解答
    - 如需人工服务，请说"转人工"
    """)
    st.divider()
    st.caption("Powered by DeepSeek + LangChain")


# 对话历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "metadata" in message:
            with st.expander("详情"):
                st.json(message["metadata"])


# 用户输入
if prompt := st.chat_input("请输入您的问题..."):
    # 添加用户消息
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用 Agent
    with st.spinner("小招正在思考中..."):
        response = agent.chat(prompt, st.session_state.session_id)

    # 添加助手消息
    st.session_state.messages.append({
        "role": "assistant",
        "content": response["answer"],
        "metadata": {
            "intent": response["intent"],
            "confidence": response["confidence"],
            "tool_used": response.get("tool_used"),
            "sources": response.get("sources", [])
        }
    })

    # 显示回复
    with st.chat_message("assistant"):
        st.markdown(response["answer"])

        # 显示意图信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"🧠 意图: {response['intent']}")
        with col2:
            st.caption(f"📊 置信度: {response['confidence']:.2f}")
        with col3:
            if response.get("tool_used"):
                st.caption(f"🔧 工具: {response['tool_used']}")

        if response.get("sources"):
            st.caption(f"📚 来源: {', '.join(response['sources'])}")


# 底部功能按钮
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💰 查询余额"):
        st.session_state.messages.append({"role": "user", "content": "查询账户余额"})
        response = agent.chat("查询账户余额", st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()

with col2:
    if st.button("📋 查账单"):
        st.session_state.messages.append({"role": "user", "content": "查询信用卡账单"})
        response = agent.chat("查询信用卡账单", st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()

with col3:
    if st.button("👤 转人工"):
        st.session_state.messages.append({"role": "user", "content": "转人工服务"})
        response = agent.chat("转人工服务", st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()