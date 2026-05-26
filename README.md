# 鎷涘晢閾惰鏅鸿兘瀹㈡湇 (CMB Smart Customer Service)

> 鍩轰簬 LangChain + DeepSeek 鐨勯摱琛屽鏈?AI 绯荤粺锛屽畬鏁村睍绀?AI 浜у搧杩愯惀鑳藉姏

## 椤圭洰鑳屾櫙

鏈」鐩槸鎷涘晢閾惰浣涘北鍒嗚 AI 鏅鸿兘瀹㈡湇鐨勫師鍨嬪疄鐜帮紝鐢ㄤ簬锛?1. **灞曠ず AI 浜у搧杩愯惀鑳藉姏**锛氬満鏅瘑鍒€佽瘎娴嬩綋绯汇€丷AG 璋冧紭銆丄gent 宸ョ▼
2. **闈㈣瘯椤圭洰缁忛獙**锛氬畬鏁寸殑绔埌绔?AI 绯荤粺锛屽寘鍚剰鍥捐瘑鍒€丷AG 妫€绱€佸杞璇濄€佽瘎娴嬩綋绯?3. **GitHub 浣滃搧闆?*锛氬睍绀哄伐绋嬪寲鑳藉姏銆佷唬鐮佽鑼冦€丆I/CD

## 鏋舵瀯鍥?
```mermaid
flowchart TB
    subgraph 鐢ㄦ埛灞?        U[鐢ㄦ埛]
    end

    subgraph 鍓嶅彴浜у搧
        UI[Streamlit 鑱婂ぉ鐣岄潰]
    end

    subgraph 涓彴鑳藉姏
        subgraph 鎰忓浘璇嗗埆["鎰忓浘璇嗗埆锛堥樁姊紡锛?]
            RE[瑙勫垯寮曟搸]
            TC[杞婚噺鍒嗙被妯″瀷]
            LLM[LLM鎰忓浘瑙ｆ瀽]
        end

        subgraph RAG["RAG 鐭ヨ瘑搴?]
            KB[鐭ヨ瘑搴揮
            IR[Chroma+BM25]
        end

        subgraph Agent["Agent 缂栨帓"]
            AG[LangChain Agent]
            MEM[瀵硅瘽璁板繂]
            TOOL[妯℃嫙宸ュ叿]
        end

        subgraph 璇勬祴["璇勬祴浣撶郴"]
            DS[璇勬祴鏁版嵁闆哴
            MET[璇勬祴鎸囨爣]
            BC[Badcase绠＄悊]
        end
    end

    U --> UI
    UI --> RE
    RE --> TC
    TC --> LLM
    LLM --> AG
    AG --> IR
    AG --> TOOL
    IR --> KB
```

## 鐩綍缁撴瀯

```
.
鈹溾攢鈹€ src/
鈹?  鈹溾攢鈹€ config.py              # 閰嶇疆鏂囦欢
鈹?  鈹溾攢鈹€ components/             # 缁勪欢妯″潡
鈹?  鈹?  鈹斺攢鈹€ intent_recognizer.py  # 闃舵寮忔剰鍥捐瘑鍒?鈹?  鈹溾攢鈹€ agent/                  # Agent 妯″潡
鈹?  鈹?  鈹溾攢鈹€ customer_service_agent.py  # 瀹㈡湇 Agent 鏍稿績
鈹?  鈹?  鈹溾攢鈹€ conversation_manager.py     # 瀵硅瘽绠＄悊鍣?鈹?  鈹?  鈹斺攢鈹€ tools.py                  # 妯℃嫙閾惰涓氬姟宸ュ叿
鈹?  鈹溾攢鈹€ rag/                    # RAG 妯″潡
鈹?  鈹?  鈹溾攢鈹€ knowledge_base.py        # 鐭ヨ瘑搴?鈹?  鈹?  鈹斺攢鈹€ retriever.py             # 娣峰悎妫€绱㈠櫒
鈹?  鈹溾攢鈹€ eval/                   # 璇勬祴妯″潡
鈹?  鈹?  鈹斺攢鈹€ evaluator.py            # 璇勬祴鍣?鈹?  鈹斺攢鈹€ api/                    # API 妯″潡
鈹?      鈹斺攢鈹€ main.py             # FastAPI 鎺ュ彛
鈹溾攢鈹€ tests/                      # 娴嬭瘯鐢ㄤ緥
鈹溾攢鈹€ knowledge_base/             # 鐭ヨ瘑搴撴枃浠?鈹溾攢鈹€ data/                       # 鏁版嵁鐩綍
鈹溾攢鈹€ .github/workflows/          # CI/CD 閰嶇疆
鈹溾攢鈹€ .env                        # 鐜鍙橀噺锛圓PI Key锛?鈹溾攢鈹€ requirements.txt           # 渚濊禆
鈹溾攢鈹€ app.py                      # Streamlit 鍓嶇鍏ュ彛
鈹斺攢鈹€ README.md
```

## 鎶€鏈爤

| 妯″潡 | 鎶€鏈?|
|------|------|
| 鍚庣 | Python 3.10 + FastAPI |
| Agent 妗嗘灦 | LangChain |
| LLM | DeepSeek API |
| RAG | Chroma + BM25 娣峰悎妫€绱?|
| 鎰忓浘璇嗗埆 | 瑙勫垯 + 杞婚噺妯″瀷 + LLM 涓夌骇鍥為€€ |
| 鍓嶇 | Streamlit |
| 璇勬祴 | 鑷缓璇勬祴妗嗘灦 |

## 蹇€熷紑濮?
### 1. 鐜鍑嗗

```bash
# 鍏嬮殕椤圭洰
git clone https://github.com/frankfang99/cmb-smart-customer-service.git
cd cmb-smart-customer-service

# 鍒涘缓铏氭嫙鐜
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 瀹夎渚濊禆
pip install -r requirements.txt
```

### 2. 閰嶇疆鐜鍙橀噺

```bash
# 澶嶅埗鐜鍙橀噺妯℃澘
cp .env.example .env

# 缂栬緫 .env锛屽～鍏ヤ綘鐨?DeepSeek API Key
DEEPSEEK_API_KEY=your_api_key_here
```

### 3. 鍚姩鏈嶅姟

**鏂瑰紡涓€锛歋treamlit 鍓嶇锛堟帹鑽愶級**
```bash
streamlit run app.py
```

**鏂瑰紡浜岋細FastAPI 鍚庣**
```bash
uvicorn src.api.main:app --reload
```

**鏂瑰紡涓夛細杩愯璇勬祴**
```bash
python -m src.eval.run_evaluation
```

## 鍔熻兘婕旂ず

### 鎰忓浘璇嗗埆锛堥樁姊紡鍥為€€锛?
```
鐢ㄦ埛: "鎴戞兂鏌ヤ竴涓嬩綑棰?
  鈹溾攢鈹€ 瑙勫垯寮曟搸: 鏈懡涓?  鈹溾攢鈹€ 杞婚噺妯″瀷: 鍛戒腑 -> account_query (0.85)
  鈹斺攢鈹€ 缁撴灉: 杩斿洖璐︽埛浣欓淇℃伅

鐢ㄦ埛: "杞处鎬庝箞鎿嶄綔"
  鈹溾攢鈹€ 瑙勫垯寮曟搸: 鍛戒腑 "杞处" -> transfer_guide (0.95)
  鈹斺攢鈹€ 缁撴灉: 杩斿洖杞处鎸囧紩
```

### RAG 鐭ヨ瘑搴撴绱?
```
鐢ㄦ埛: "淇＄敤鍗¤繕娆炬柟寮忔湁鍝簺"
  鈹溾攢鈹€ 鍚戦噺妫€绱? 鎵惧埌 "bill_002" (0.89)
  鈹溾攢鈹€ BM25妫€绱? 鎵惧埌 "bill_001" (0.75)
  鈹斺攢鈹€ RRF铻嶅悎: 杩斿洖鏈€浣冲尮閰?```

### 璇勬祴浣撶郴

| 鎸囨爣 | 鍊?|
|------|---|
| 鎰忓浘鍑嗙‘鐜?| 85%+ |
| 鍥炵瓟鐩镐技搴?| 80%+ |
| 缁煎悎寰楀垎 | 82%+ |

## AI 浜у搧杩愯惀鑳藉姏鏄犲皠

| 鑳藉姏椤?| 鍦ㄩ」鐩腑鐨勪綋鐜?|
|--------|---------------|
| 涓氬姟鍦烘櫙璇嗗埆 | 閾惰瀹㈡湇鍦烘櫙閫夋嫨锛孎AQ + 浠诲姟鍨嬪璇?|
| RAG 鐭ヨ瘑搴?| 鐭ヨ瘑搴撶粨鏋勮璁°€佹绱㈣皟浼樸€丅adcase 鍥炴祦 |
| 璇勬祴浣撶郴 | 璇勬祴闆嗘瀯閫犮€佹寚鏍囧畾涔夈€佹姤鍛婄敓鎴?|
| Agent 宸ョ▼ | 鎰忓浘璇嗗埆銆佸伐鍏疯皟鐢ㄣ€佸杞璇?|
| 鏁版嵁椹卞姩 | 杞寲婕忔枟鍒嗘瀽銆佹晥鏋滃鐩?|

## 寮€鍙戞寚鍗?
### 娣诲姞鏂扮殑鎰忓浘绫诲瀷

缂栬緫 `src/components/intent_recognizer.py`锛?
```python
class IntentType(str, Enum):
    # ... 鐜版湁鎰忓浘
    NEW_INTENT = "new_intent"  # 鏂板

    # 娣诲姞鍒拌鍒欐槧灏?    RULE_MAPPINGS = {
        # ...
        "鏂板叧閿瘝": IntentType.NEW_INTENT,
    }
```

### 鎵╁睍鐭ヨ瘑搴?
缂栬緫 `src/rag/knowledge_base.py`锛?
```python
KNOWLEDGE_BASE.append({
    "id": "new_001",
    "category": "new_category",
    "question": "鏂伴棶棰?,
    "answer": "鏂板洖绛?,
    "tags": ["鏍囩"],
    "metadata": {"intent": "new_intent", "frequency": "medium"}
})
```

### 娣诲姞鏂板伐鍏?
缂栬緫 `src/agent/tools.py`锛?
```python
@staticmethod
def new_tool(param: str) -> ToolResult:
    """鏂板伐鍏疯鏄?""
    return ToolResult(
        success=True,
        data={},
        message="宸ュ叿杩斿洖",
        tool_name="new_tool"
    )

# 娉ㄥ唽鍒?BANKING_TOOLS
BANKING_TOOLS["new_tool"] = BankingTools.new_tool
```

## CI/CD

椤圭洰浣跨敤 GitHub Actions 鑷姩锛?- 浠ｇ爜鏍煎紡妫€鏌ワ紙Black銆乮sort锛?- Lint 妫€鏌ワ紙flake8锛?- 鍗曞厓娴嬭瘯锛坧ytest锛?- 璇勬祴闆嗛獙璇?
## 鍚庣画浼樺寲鏂瑰悜

- [ ] 鎺ュ叆鐪熷疄閾惰 API锛堥潪妯℃嫙锛?- [ ] 澧炲姞鏇村鎰忓浘绫诲瀷
- [ ] 瀹屽杽璇勬祴闆嗭紙鐩爣 500+ 鏉★級
- [ ] 鎺ュ叆鍓嶇妗嗘灦锛圧eact/Vue锛?- [ ] 娣诲姞鐢ㄦ埛婊℃剰搴﹀弽棣?- [ ] 瀹炵幇瀹炴椂鐩戞帶闈㈡澘

## License

MIT