# -*- coding: utf-8 -*-
"""
Streamlit Chat Interface
"""
import streamlit as st
from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings
import uuid


# Page Config
st.set_page_config(
    page_title="CMBC Smart Customer Service",
    page_icon="🏦",
    layout="centered"
)

# Initialize Agent
@st.cache_resource
def init_agent():
    return CustomerServiceAgent(settings)

agent = init_agent()

# Session Management
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = True


# Title
st.title("🏦 CMBC Smart Customer Service")
st.markdown("Hello! I'm the CMBC Smart Assistant. How can I help you today?")

# Sidebar
with st.sidebar:
    st.header("📌 Features")
    st.markdown("""
    **Services Supported:**
    - Account Balance Query
    - Credit Card Bill Query
    - Branch Location Query
    - Wealth Products Inquiry
    - Transfer Guidance
    - Card Loss Report
    - Human Service Transfer

    **Usage Tips:**
    - Enter your question and I'll do my best to help
    - For human agent, say "transfer to human"
    """)
    st.divider()
    st.caption("Powered by DeepSeek + LangChain")


# Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "metadata" in message:
            with st.expander("Details"):
                st.json(message["metadata"])


# User Input
if prompt := st.chat_input("Please enter your question..."):
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Processing..."):
        response = agent.chat(prompt, st.session_state.session_id)

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

    with st.chat_message("assistant"):
        st.markdown(response["answer"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"🧠 Intent: {response['intent']}")
        with col2:
            st.caption(f"📊 Confidence: {response['confidence']:.2f}")
        with col3:
            if response.get("tool_used"):
                st.caption(f"🔧 Tool: {response['tool_used']}")

        if response.get("sources"):
            st.caption(f"📚 Sources: {', '.join(response['sources'])}")


# Quick Action Buttons
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💰 Query Balance"):
        st.session_state.messages.append({"role": "user", "content": "Query account balance"})
        response = agent.chat("Query account balance", st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()

with col2:
    if st.button("📋 Check Bill"):
        st.session_state.messages.append({"role": "user", "content": "Query credit card bill"})
        response = agent.chat("Query credit card bill", st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()

with col3:
    if st.button("👤 Transfer"):
        st.session_state.messages.append({"role": "user", "content": "Transfer to human service"})
        response = agent.chat("Transfer to human service", st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()