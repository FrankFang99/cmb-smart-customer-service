"""
Streamlit 鑱婂ぉ鐣岄潰
"""
import streamlit as st
from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings
import uuid


# 椤甸潰閰嶇疆
st.set_page_config(
    page_title="鎷涘晢閾惰鏅鸿兘瀹㈡湇",
    page_icon="馃彟",
    layout="centered"
)

# 鍒濆鍖?Agent
@st.cache_resource
def init_agent():
    return CustomerServiceAgent(settings)

agent = init_agent()

# 浼氳瘽绠＄悊
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = True


# 鏍囬
st.title("馃彟 鎷涘晢閾惰鏅鸿兘瀹㈡湇")
st.markdown("鎮ㄥソ锛佹垜鏄皬鎷涙櫤鑳藉鏈嶏紝鏈変粈涔堝彲浠ュ府鎮紵")

# 渚ц竟鏍?- 鍔熻兘浠嬬粛
with st.sidebar:
    st.header("馃搶 鍔熻兘璇存槑")
    st.markdown("""
    **鏀寔鐨勬湇鍔★細**
    - 璐︽埛浣欓鏌ヨ
    - 淇＄敤鍗¤处鍗曟煡璇?    - 缃戠偣鍦板潃鏌ヨ
    - 鐞嗚储浜у搧鍜ㄨ
    - 杞处鎿嶄綔鎸囧紩
    - 鍗＄墖鎸傚け鏈嶅姟
    - 杞汉宸ユ湇鍔?
    **浣跨敤鎻愮ず锛?*
    - 杈撳叆鎮ㄧ殑闂锛屽皬鎷涗細灏藉姏瑙ｇ瓟
    - 濡傞渶浜哄伐鏈嶅姟锛岃璇?杞汉宸?
    """)
    st.divider()
    st.caption("Powered by DeepSeek + LangChain")


# 瀵硅瘽鍘嗗彶
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "metadata" in message:
            with st.expander("璇︽儏"):
                st.json(message["metadata"])


# 鐢ㄦ埛杈撳叆
if prompt := st.chat_input("璇疯緭鍏ユ偍鐨勯棶棰?.."):
    # 娣诲姞鐢ㄦ埛娑堟伅
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # 璋冪敤 Agent
    with st.spinner("灏忔嫑姝ｅ湪鎬濊€冧腑..."):
        response = agent.chat(prompt, st.session_state.session_id)

    # 娣诲姞鍔╂墜娑堟伅
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

    # 鏄剧ず鍥炲
    with st.chat_message("assistant"):
        st.markdown(response["answer"])

        # 鏄剧ず鎰忓浘淇℃伅
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"馃 鎰忓浘: {response['intent']}")
        with col2:
            st.caption(f"馃搳 缃俊搴? {response['confidence']:.2f}")
        with col3:
            if response.get("tool_used"):
                st.caption(f"馃敡 宸ュ叿: {response['tool_used']}")

        if response.get("sources"):
            st.caption(f"馃摎 鏉ユ簮: {', '.join(response['sources'])}")


# 搴曢儴鍔熻兘鎸夐挳
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("馃挵 鏌ヨ浣欓"):
        st.session_state.messages.append({"role": "user", "content": "鏌ヨ璐︽埛浣欓"})
        response = agent.chat("鏌ヨ璐︽埛浣欓", st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()

with col2:
    if st.button("馃搵 鏌ヨ处鍗?):
        st.session_state.messages.append({"role": "user", "content": "鏌ヨ淇＄敤鍗¤处鍗?})
        response = agent.chat("鏌ヨ淇＄敤鍗¤处鍗?, st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()

with col3:
    if st.button("馃懁 杞汉宸?):
        st.session_state.messages.append({"role": "user", "content": "杞汉宸ユ湇鍔?})
        response = agent.chat("杞汉宸ユ湇鍔?, st.session_state.session_id)
        st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
        st.rerun()