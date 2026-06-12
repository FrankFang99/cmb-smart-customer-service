# 招商银行智能客服 (CMB Smart Customer Service)

> 基于 LangChain + DeepSeek 的银行客服 AI 系统
> **抽象 RAGAS 工业级框架 + 银行业务调整（Adapter 模式）+ Harness 工程搭建式评测**

[![评测](https://img.shields.io/badge/RAGAS-4%E5%A4%A7%E6%8C%87%E6%A0%87-blue)]()
[![业务](https://img.shields.io/badge/%E4%B8%9A%E5%8A%A1-FCR%2FCSAT%2F%E9%92%B1%E6%95%88-green)]()
[![方法论](https://img.shields.io/badge/%E6%96%B9%E6%B3%95%E8%AE%BA-%E4%B8%9A%E7%95%8C%E5%89%8D%E6%B2%BF-orange)]()
[![评测](https://img.shields.io/badge/%E8%AF%84%E6%B5%8B-v3.4.0_Cascade-blueviolet)]()
[![Cascade](https://img.shields.io/badge/Cascade-L1%2FL2%2FL3-success)]()
[![Badcase](https://img.shields.io/badge/Badcase-%E6%A0%87%E6%B3%AA%E6%B1%A0-critical)]()

---

## 一、项目定位

本项目是面向 **AI 产品运营** 求职的作品集，对齐业界（2025-2026）最前沿的方法论：

| 维度 | 业界事实标准 | 本项目实现 |
|------|--------------|-----------|
| **评测框架** | RAGAS（GitHub 4k+ stars） | ✅ `eval_runner_v6.py` 4 大核心指标 + 3 项业务扩展 |
| **业务指标** | 客服中心四象限（CSAT/FCR/转人工率/响应时长） | ✅ `business_metrics.py` 7 大指标 + 分层 + 钱效 |
| **分层策略** | L1/L2/L3 复杂度分层 | ✅ 招行实战分层映射 |
| **Badcase 管理** | P0/P1/P2 自动定级 | ✅ `BadcaseAnalyzer` 24h/3d/1w 响应 + **v3.4.0 标注池 + 一键入 KB** |
| **钱效模型** | Uplift Model | ✅ ROI + 净节省 + 单次成本对比 |
| **★ Harness 工程评测** | CMU/Yale Survey ETCLOVG 七层架构 | ✅ v3.2 评测方案：L1/L2/L3 + 三大评估缺口 + 协同增强视角 |
| **★ Cascade 路由 (v3.4.0)** | Anthropic / LangGraph / AWS Bedrock Agent | ✅ L1 模板 + L2 RAG + L3 LLM 三级路由，**LLM 调用率 6.83%，节省 93.2%** |

---

## 二、架构

```mermaid
flowchart TB
    subgraph 用户层
        U[95555 用户]
    end

    subgraph 前台产品
        UI[Streamlit 聊天界面]
    end

    subgraph 中台能力
        subgraph 意图识别["意图识别 - 阶梯式"]
            RE[规则引擎<br/>17级优先级]
            TC[轻量分类模型]
            LLM[LLM意图解析]
        end

        subgraph RAG["RAG 知识库"]
            KB[知识库<br/>565条业务知识 v2.0]
            IR[Chroma + BM25<br/>混合检索]
        end

        subgraph Agent["Agent 编排"]
            AG[LangChain Agent]
            MEM[对话记忆]
            TOOL[模拟工具集]
        end
    end

    subgraph 评测层["评测层 - 对齐 RAGAS + Harness 7层"]
        FAITH[Faithfulness]
        ANS[Answer Relevancy]
        CTX_P[Context Precision]
        CTX_R[Context Recall]
        INTENT[Intent Accuracy]
        TOOL_A[Tool Call Accuracy]
        COMP[Compliance Safety]
        COST[★ 运营成本子指标<br/>Step/Token/工具调用]
        SEC[★ 安全审计子指标<br/>权限/PII/红线]
        TRAJ[★ 轨迹级评估<br/>过程可见性]
    end

    subgraph 业务层["业务层 - 四象限"]
        CSAT_KPI[CSAT / FCR]
        TRANS_KPI[转人工率分层]
        RT_KPI[P95 响应时长]
        ROI_KPI[Uplift 钱效]
    end

    U --> UI
    UI --> RE
    RE --> TC
    TC --> LLM
    LLM --> AG
    AG --> IR
    AG --> TOOL
    IR --> KB

    AG -.评测.-> FAITH
    AG -.评测.-> ANS
    AG -.评测.-> CTX_P
    AG -.评测.-> CTX_R
    AG -.业务.-> INTENT
    AG -.业务.-> TOOL_A
    AG -.业务.-> COMP
    AG -.v3.2.-> COST
    AG -.v3.2.-> SEC
    AG -.v3.2.-> TRAJ

    AG -.业务.-> CSAT_KPI
    AG -.业务.-> TRANS_KPI
    AG -.业务.-> RT_KPI
    AG -.业务.-> ROI_KPI
```

---

## 三、核心模块

### 3.1 评测引擎 v6.0（对齐 RAGAS）

**文件**：`src/eval/eval_runner_v6.py` （733 行）

#### RAGAS 4 大核心指标

| 指标 | 公式 | 业务含义 | 目标阈值 |
|------|------|----------|----------|
| **Faithfulness（忠实度）** | 可被上下文支持的 claim 数 / 总 claim 数 | 防幻觉，金融场景硬指标 | ≥ 0.90 |
| **Answer Relevancy** | 逆向问题生成 + 余弦相似度均值 | 防答非所问、含冗余信息 | ≥ 0.85 |
| **Context Precision** | 排名 k 之前的相关片段数 / k | 检索精准度 | ≥ 0.80 |
| **Context Recall** | ground_truth 中可被 contexts 支撑的陈述数 | 知识库覆盖度 | ≥ 0.85 |

#### 业务侧扩展 3 项

| 指标 | 说明 | 目标阈值 |
|------|------|----------|
| **Intent Accuracy** | 核心 + 次要意图完全匹配 | ≥ 0.85 |
| **Tool Call Accuracy** | 工具名称 + 参数全部正确 | ≥ 0.90 |
| **Compliance Safety** | 未触发诈骗/洗钱/敏感信息泄露 | ≥ 0.98 |

**为什么选择 RAGAS**：
- GitHub 4k+ stars，工业界事实标准
- 论文 ArXiv:2309.15217，被阿里、腾讯、字节等大厂引用
- 评测指标无参考（reference-free），适合真实业务场景

### 3.2 业务指标体系 v1.0

**文件**：`src/eval/business_metrics.py` （567 行）

#### 7 大业务指标 + 分层

| 分类 | 指标 | 定义 | L1 / L2 / L3 目标 |
|------|------|------|-------------------|
| **效率层** | P50/P95 响应时长 | 秒级 | 1.0s / 2.5s / 5.0s |
| **质量层** | FCR（首次解决率） | 一次解决会话 / 总会话 | 90% / 75% / 50% |
| **质量层** | 转人工率 | 转人工 / 总会话 | 5% / 15% / 50% |
| **体验层** | CSAT | 用户主动评分 1-5 | 4.5 / 4.2 / 4.0 |
| **体验层** | NPS | 推荐者-贬损者 | 50 / 35 / 20 |
| **成本层** | 单次成本 | LLM+人力综合 | 0.5 / 1.0 / 3.0 元 |
| **成本层** | Uplift ROI | 净节省 / 投入 | 800% / 500% / 200% |

#### 四象限联动诊断

业界方法论：单看一个指标会被骗，必须联动看。

| 模式 | 诊断 | 根因 | 行动 |
|------|------|------|------|
| **A** | 回复快 + 转人工高 = 没用 | 知识库不够 / 意图不准 | 扩 FAQ |
| **B** | FCR 高 + CSAT 低 = 没共情 | 话术生硬 | 加情感识别 |
| **C** | 转人工低 + CSAT 低 = 硬撑 | 转人工阈值过高 | 降阈值 |
| **D** | 响应慢 + FCR 高 = 靠谱 | 检索慢 | 加流式输出 |

#### Uplift Model 钱效

```
净节省 = AI 替代人力成本 - AI 自身成本
ROI = 净节省 / AI 投入 × 100%
```

实测：单次 AI 服务 3.3 元 vs 人工 4.2 元，节省 20%。

### 3.3 Badcase 周会分析器

**文件**：`src/eval/business_metrics.py:BadcaseAnalyzer`

- 每周抽 30 条（10 转人工 + 10 差评 + 10 假解决）
- 自动分类（合规/金钱/知识/不匹配/边界）
- 自动定级（P0 24h / P1 3d / P2 1w）
- 输出 actionable 修复清单

### 3.4 意图识别

**文件**：`src/components/intent_recognizer.py`

- 17 级规则优先级（P0 > CARD_ACTIVATE > CARD > PASSWORD > ...）
- 覆盖 31 种意图，准确率 83.5%（600 条评测）
- 支持多意图识别（core_intent + secondary_intent）

### 3.5 RAG 知识库 (v3.3.5 业界 4 阶段 pipeline)

**文件**：`src/rag/knowledge_base.py`（v2.0 565 条 已注入） + 源文档 `knowledge_base/银行零售业务知识库_v2.0.md`

- **565 条业务知识**（v2.0, 14 业务领域 × 8 意图分类）
- 14 大业务领域：账户/信用卡/贷款/理财/支付/数字人民币/养老金/政务/跨境/便民/新就业/服务/风控/产品
- 8 大意图分类：query/consult/transaction/marketing/service_transfer/risk/complex/invalid
- 注入脚本：`scripts/import_v2_kb.py`（从 markdown 表格解析）
- 统计接口：`get_knowledge_stats()` / `get_knowledge_by_domain()` / `get_knowledge_by_intent()`

**RAG 4 阶段 Pipeline (v3.3.5 业界标准, 0 外部模型依赖)**:

```
┌─────────────────────────────────────────────────────────────────┐
│  召回阶段 (Recall)                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Multi-Query  │  │    Hybrid    │  │   Sparse     │          │
│  │ (HyDE 降级)  │  │  (RRF 融合)  │  │  (BM25字符)  │          │
│  │ 关键词扩展 +  │  │  BM25 +      │  │  字符 2-gram │          │
│  │ 同义词替换    │  │  TF-IDF+余弦  │  │  3-gram      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         └─────────────────┴──────────────────┘                  │
│                          ↓ RRF 融合                              │
├─────────────────────────────────────────────────────────────────┤
│  精排阶段 (Rerank)                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  多信号加权 Reranker                                       │  │
│  │  - 原始 retriever 分数 (RRF/余弦)        0.40            │  │
│  │  - question 关键词 2-gram 命中            0.20            │  │
│  │  - domain 业务领域匹配                    0.15            │  │
│  │  - tags 风险标签匹配                      0.15            │  │
│  │  - L0 上下文优先级 (诈骗/AML 优先 risk)   0.10            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓ top-K                                  │
└─────────────────────────────────────────────────────────────────┘
```

**业界对标 (2024-2026 主流, 本项目 0 依赖实现)**:

| 阶段 | 业界标准 | 本项目 v3.3.5 实现 | 差异 |
|------|----------|--------------------|------|
| Sparse 召回 | BM25 (Elastic / Lucene) | 字符 2-gram + 3-gram | 算法近似, 0 依赖 |
| Dense 召回 | sentence-transformers / BGE / m3e / Cohere Embed | **TF-IDF + 余弦 (sklearn)** | 用词频向量代替 embedding, 0 模型下载 |
| Multi-Query | LangChain MultiQueryRetriever (LLM 生成变体) | **关键词扩展 + 同义词词典** | 规则代替 LLM, 0 依赖 |
| HyDE | Gao et al. 2022 (LLM 生成假设答案) | 关键词提取 + 子问题拆分 | 0 依赖降级版 |
| Hybrid 融合 | Pinecone / Elastic RRF (Cormack 2009) | **RRF 公式 k=60** | 算法 1:1 对齐 |
| Rerank | Cohere Rerank 3 / BGE Reranker v2 / Jina | **多信号加权 (5 信号)** | 0 模型, 业务定制权重 |

**RAG 文件结构**:

```
src/rag/
├── knowledge_base.py          # 知识库 v2.0 565 条
├── simple_retriever.py        # Sparse: 字符 2-gram BM25
├── dense_retriever.py         # Dense: TF-IDF + 余弦 (sklearn)
├── hybrid_retriever.py        # Hybrid: BM25 + Dense + RRF
├── multi_query_retriever.py   # Multi-Query + HyDE 降级
└── reranker.py                # Rerank: 多信号加权
```

**验证**: 14 query 5 retriever 全部 14/14 = 100% 命中 (Reranked 排序质量最优)

### 3.5.1 端到端 Pipeline (v3.3.8 真业务流串联)

**文件**: `src/agent/e2e_pipeline.py` (~270 行, 0 LangChain 依赖)

**完整业务流** (5 阶段, 业界标准 Agent 架构):

```
┌─────────────────────────────────────────────────────────────────┐
│  用户输入 "我信用卡被盗刷了 5000 块"                              │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  1. 意图识别 (IntentRecognizer, 17 级规则)                       │
│     识别: sec_stolen_card (置信度 0.95)                         │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. L0 红线检测 (banking_l0_dict.check_l0, 268 词词典)         │
│     触发: fraud_high_risk (P0 严重)                             │
└──────────────────────────────┬──────────────────────────────────┘
                               ↓
                ┌──────────────┴──────────────┐
                ↓                             ↓
        L0 触发 (银行业强约束)            L0 不触发
                ↓                             ↓
┌────────────────────────────┐  ┌──────────────────────────────────┐
│  3a. 标准话术模板             │  │  3b. RAG 4 阶段检索               │
│  L0_RESPONSE_TEMPLATES       │  │  (Sparse + Dense + MultiQuery     │
│  + 转人工 (transfer_human)   │  │   + Rerank)                      │
│  AI 不调 LLM 答业务           │  │  返回 top-3 知识                  │
│  0ms 极速 (银行业硬约束)      │  └──────────────┬───────────────────┘
└────────────────────────────┘                 ↓
                                      ┌──────────────────────────────────┐
                                      │  4. 业务 context 拼装             │
                                      │  - 历史对话 (4 轮)               │
                                      │  - 参考知识 (3 条)               │
                                      │  - 意图 + 风险提示约束            │
                                      └──────────────┬───────────────────┘
                                                     ↓
                                      ┌──────────────────────────────────┐
                                      │  5. LLM 生成 (MiniMax-M2.7)       │
                                      │  - 订阅 Key + api.minimaxi.com    │
                                      │  - 系统提示含风险披露             │
                                      │  - 贷款类强制年化利率             │
                                      │  - 控制在 200 字内                │
                                      └──────────────┬───────────────────┘
                                                     ↓
                                      ┌──────────────────────────────────┐
                                      │  6. 回答返回 + 会话记录            │
                                      │  ConversationManager 维护上下文   │
                                      └──────────────────────────────────┘
```

**业界对应 (2024-2026 主流 Agent 框架)**:

| 框架 | 核心架构 | 本项目 |
|------|----------|--------|
| LangGraph | Node + Edge + State graph | 顺序 5 阶段 + 单一 IntentRecognizer + RerankedRetriever + LLM |
| LlamaIndex QueryEngine | Retriever + Synthesizer | 4 阶段 RerankedRetriever + minimax chat |
| Haystack Pipeline | Node DAG | 顺序 5 阶段 |
| AWS Bedrock Agent | Action Group + Knowledge Base | L0 强约束 + RAG + LLM 决策 |

**0 外部框架依赖** (本项目优势):
- 不依赖 langchain / langgraph / llamaindex / haystack
- 自有 IntentRecognizer (17 级规则)
- 自有 RerankedRetriever (4 阶段, 业界标准)
- 自有 minimax_client (订阅 Key 直连)
- 业务定制更灵活 (L0 强约束 / 风险披露 / 监管话术 都可嵌)

**5 个真业务流验证 (v3.3.8)**:

| 业务流 | 意图 | L0 触发 | 动作 | 耗时 | 状态 |
|--------|------|---------|------|------|------|
| L0 信用卡盗刷 | sec_stolen_card (0.95) | ✓ | transfer_human | 0ms | OK |
| L0 假冒银监会 | sys_invalid (0.0) | ✓ | transfer_human | 16ms | OK |
| L1 信用卡激活 | biz_card_activate (0.95) | ✗ | answer + LLM | 1832ms | OK |
| L2 理财保本 | sys_invalid (0.0) | ✗ | answer + LLM | 7119ms | OK |
| L1 招行五险一金 | sys_invalid (0.0) | ✗ | answer + LLM | 1666ms | OK |

**5/5 业务流 OK** (L0 0ms 极速不调 LLM, 业务流 1.6-7.1s 含 RAG + LLM)

**用法**:
```python
from src.agent.e2e_pipeline import create_e2e_pipeline
pipeline = create_e2e_pipeline()
result = pipeline.handle("我信用卡被盗刷了", session_id="s1")
print(result['answer'], result['action'])
# 回答 + action: 'transfer_human' / 'answer' / 'error'
```

### 3.6 ★ 评测方案 v3.2（Harness 工程搭建式 + Survey 七层架构）

**文件**：`docs/评测评分标准_v3.2.md`（29 KB / 23 页 PDF）

**核心升级**（v3.1 → v3.2）：

| 维度 | v3.1 | v3.2 |
|------|------|------|
| 理论锚点 | 凭经验 | **对齐 CMU/Yale Survey 的 ETCLOVG 七层架构** |
| 评估盲区 | 没识别 | **新增三大评估缺口**（安全 / 运营成本 / 模型 vs Harness 分离） |
| 进化视角 | 无 | **新增 Harness 工程三层次**（行动接口 → 工作流 → 用户中心持久化） |
| 协同优化 | 只讲 Harness 端 | **新增协同增强视角**（Harness + 模型双轨） |
| 评测粒度 | 结果级 | **新增轨迹级评估**（过程可见性） |
| 错误分类 | 7 类 | **新增 TRAJECTORY_DEVIATION / COST_OVERRUN / SECURITY_VIOLATION 3 类** |

**v3.2 三层指标框架（L1/L2/L3）+ ETCLOVG 映射**：

| 本项目指标层 | ETCLOVG 映射 | 含义 |
|------------|-------------|------|
| L1 通用基础 | E + T + C | 必报——脱离这三层 Agent 跑不起来 |
| L2 能力型 | L + O | 按能力勾选——单步 vs 多步、确定性 vs 概率性 |
| L3 专属 | V + G | 按业务追加——银行业加合规 / 红线 / Adapter |

**v3.2 评测集 system.question 新增 3 个字段**：
- `expected_trajectory`（轨迹级评估）
- `cost_expectation`（运营成本评估）
- `security_expectation`（安全审计评估）

**理论参考**：
- CMU/Yale/Amazon《Agent Harness Engineering: A Survey》（OpenReview: eONq7FdiHa, 2026）
- 《Agent Systems with Harness Engineering》（OpenReview: nM5tDHrQsx, 2026）
- 阿里云泊予《基于顶级 Agent 的 Harness 工程搭建式业务 Agent 评测方案》

---

## 四、目录结构

```
.
├── src/
│   ├── config.py
│   ├── components/
│   │   └── intent_recognizer.py          # 阶梯式意图识别
│   ├── agent/
│   │   ├── customer_service_agent.py     # 客服 Agent
│   │   ├── conversation_manager.py       # 对话管理
│   │   └── tools.py                      # 模拟工具
│   ├── rag/
│   │   ├── knowledge_base.py             # 知识库
│   │   └── retriever.py                  # 混合检索
│   └── eval/
│       ├── eval_runner_v6.py             # ★ v6 对齐 RAGAS（最新）
│       ├── business_metrics.py           # ★ 业务四象限指标
│       └── banking_adapter.py            # ★ 银行业务 Adapter
├── data/
│   ├── evaluation_dataset_v5.1.json      # ★ 600 条黄金评测集
│   ├── eval_results.json                 # 最新评测结果
│   ├── eval_report.md                    # 评测报告
│   └── generate_dataset.py               # 评测集生成器
├── scripts/
│   ├── md_to_docx_v31.py                 # md → docx（v3.1）
│   ├── md_to_docx_v32.py                 # md → docx（v3.2）
│   └── docx_to_pdf.py                    # docx → PDF
├── docs/                                  # 评测方法论文档
│   ├── 评测评分标准_v3.2.md/.docx/.pdf   # ★ Harness 7 层 + 三大缺口
│   ├── 评测评分标准_v3.0.md
│   ├── 评测指标体系_v1.0.md / v1.1.md
│   ├── 业务指标体系_v2.0.md
│   └── 银行业务知识库_v2.0.md
├── knowledge_base/                        # 银行业务知识库 v2.0 (565 条)
├── tests/
├── .github/workflows/                     # CI/CD
├── app.py                                 # Streamlit 前端
├── AI智能客服项目_复盘_v2.2.pdf           # 面试用项目复盘（6 页）
├── 面试题库_v2.2.pdf                     # 面试用题库（12 页）
└── README.md
```

---

## 五、技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10 + FastAPI |
| Agent | LangChain |
| LLM | DeepSeek API |
| RAG | Chroma + BM25 混合检索 |
| 意图识别 | 规则 + 模型 + LLM 三级回退 |
| 评测 | RAGAS 对齐 + 自研业务指标 + ★ Harness 工程搭建式评测 v3.2 |
| 前端 | Streamlit |
| CI/CD | GitHub Actions |

---

## 六、快速开始

```bash
# 克隆项目
git clone https://github.com/FrankFang99/cmb-smart-customer-service.git
cd cmb-smart-customer-service

# 安装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 填入 DEEPSEEK_API_KEY

# 启动 Streamlit 前端
streamlit run app.py

# 跑 RAGAS 评测
python -m src.eval.eval_runner_v6

# 跑业务指标
python -m src.eval.business_metrics
```

---

## 七、v3.4.0 Cascade 路由 + Badcase 闭环

### 7.1 Cascade 路由 (业界头部做法)

**业界对齐**: Anthropic (Haiku/Opus), LangGraph conditional edges, AWS Bedrock Agent 都在 2025-2026 转向 Cascade 路由.

**思路**:
| Level | 触发条件 | 响应 | LLM 调用 |
|-------|---------|------|---------|
| **L1** | 高置信 (≥0.9) + 模板可答 | 银行业模板库 (35+ 业务) | 不调 |
| **L2** | 中置信 (≥0.7) + RAG 命中 | 知识库 Top-1 直接答 | 不调 |
| **L3** | 低置信 / 模糊 / 边界 | 调 LLM 兜底 | 调 |
| **L0** | P0 红线 / 投诉 / 紧急 | 100% 转人工 | 不调 |

**600 样本实测** (v3.4.0):
| 指标 | 数值 | v3.2 对比 |
|------|------|---------|
| **意图准确率** | 83% | 52.5% → **+30.5pp** |
| **L0 Compliance** | 100% | 94.25% → +5.75pp |
| **RAG 命中率** | 98.75% | 57.4% → +41.35pp |
| **LLM 调用率** | 6.83% | 100% → **-93.17pp** (节省) |

**Cascade 路由分布** (600 样本):
- L1 模板: 360 (60.0%)
- L2 RAG 命中: 157 (26.2%)
- L3 LLM 兜底: 41 (6.8%)
- L0 转人工: 42 (7.0%)
- **累计 86.2% 不调 LLM**

### 7.2 RAG 4 阶段 Pipeline (v3.3.5)

**业界对齐**: Anthropic Contextual Retrieval, LangGraph RAG, AWS Kendra

| 阶段 | 方法 | 实现 |
|------|------|------|
| 1. Sparse 检索 | BM25 字符 2-gram + 银行业停用词 | `simple_retriever.py` |
| 2. Dense 检索 | TF-IDF + 余弦 (sklearn) | `dense_retriever.py` |
| 3. Multi-Query | 同义词扩展 + HyDE 降级 | `multi_query_retriever.py` |
| 4. Reranker | 多信号加权 (5 信号) | `reranker.py` |

**混合**: RRF (Cormack 2009, k=60) 融合 1+2 + 3+4 多级。

### 7.3 Badcase 标注池 (v3.4.0-a)

**业界对齐**: B 站「亚慧 AI 产品经理」(BV1vKuJzpEbc) — 「没有评估就没有迭代」, 「PM 价值核心是 Bad Case 闭环」.

**实现** (`src/eval/badcase_pool.py`):
- JSONL 持久化池 (git 友好)
- 自动定级 (P0/P1/P2) + 自动初判根因
- 5 类根因: `intent_mismatch / retrieval_miss / l0_false_trigger / l0_miss_trigger / cascade_routing_err`
- 6 类修复动作: `add_faq / adjust_threshold / add_intent_pattern / transfer_to_human / ignore / pending`
- **一键入知识库** (`add_faq_to_kb`) — 标注完直接入 KB
- 周会分析 (`weekly_summary`) — 根因分布 + 修复率 + P0/P1 待办

**13 条真实 badcase (v3.4.0 失败样本)**:
- intent_mismatch: 8 (62%)
- l0_miss_trigger: 5 (38%)
- 5 P0 待办 + 8 P1 待办
- 演示标注 4 条 + 入 KB 1 条 + 修复率 7.7%

**使用**:
```bash
# 入池
python scripts/eval_badcase.py

# 演示标注
python scripts/eval_badcase_demo.py

# 周会分析
python -m src.eval.badcase_pool summary
```

---

## 七、v3.4.0-b 知识库分类 + 5 路径路由 + 多模板管理 (2026-06-12)

> 继 v3.4.0 Cascade 路由 + Badcase 闭环后,本次从"扁平 565 条"升级为"分类 + 路由 + 多模板"实战架构。对标招行 / 微众 / 蚂蚁 2025-2026 工业级做法。

### 7.1 知识库 3 类库分类 (v3.4.0-b-1)

**业界对齐**: 银行业实战必须 3 类起步 —— 文档库 / FAQ 库 / 业务数据库 (up 主 BV1vKuJzpEbc 原话)

**实现** (`src/rag/knowledge_base_v2.py`):
- 565 条 v2.0 自动拆分为 **3 类 + 7 chunk 策略**:
  - `doc_kb` 280 条 (query/transaction/risk 类)
  - `faq_kb` 285 条 (consult/marketing 类, qa_pair 策略)
  - `biz_db` 0 条 (招行实战 3 表 mock: orders/products/logistics)
- **Chunking 策略选择器** (7 种):
  - `smart` 智能语义 (默认)
  - `by_heading` 按标题 (Markdown / 文档)
  - `qa_pair` 按 QA 对 (FAQ)
  - `by_row` 按行 (CSV / 表格)
  - `full_table` 整表 (小型参数表)
  - `by_endpoint` 按 endpoint (API 文档)
  - `by_dialogue` 按对话回合 (客服录音)

**业务数据库 mock** (招行实战 3 类):
- 5 个示例客户 (C001-C005)
- 4 个订单 (信用卡账单 + 交易订单)
- 5 个产品 (2 信用卡 + 1 贷款 + 2 理财)
- 2 个物流 (卡片邮寄 + 对账单邮寄)
- API 接口: `query_bill_amount / query_transaction_record / query_logistics / query_product`

### 7.2 5 路径路由决策器 (v3.4.0-b-2)

**业界对齐**: 招行小招 / 微众银行 / 蚂蚁客服 2025-2026 都在转向 5 路径路由

**5 条路径** (按优先级):
| 优先级 | 路径 | 触发条件 | 响应 |
|--------|------|---------|------|
| 1 | `L0_HUMAN` | L0 红线 / 紧急转人工 | 100% 转人工 |
| 2 | `BIZ_DB_API` | 账单/余额/物流查询 | 调业务数据库 (Text2SQL/API) |
| 3 | `AGENT_TOOL` | 激活/挂失/还款等工具意图 | **v3.4.0 暂不做, 给跳转接口** |
| 4 | `RAG_KB` | 信息咨询/营销 | RAG 4 阶段检索 |
| 5 | `CASCADE_TEMPLATE` | 业务办理/兜底 | Cascade 模板 |

**产品决策** (面试必讲):
> "工具意图 v3.4.0 暂不做真实工具调用 —— 银行真实工具调用涉及身份鉴权 4 要素 / 工单审批 3 级 / 银保监审计 6 年 / 灾备 SLA 99.99% 4 大风险。**业务上'不确定能交付的能力不要承诺'**。v3.4.0 替代方案: 给跳转接口 (招行 App / 95555)。v3.5.0 计划加 mock read-only 工具。"

**实现** (`src/agent/route_decision.py`):
- `RouteDecision` 数据类: path / reason / priority / intent / target_resource / fallback
- 决策可观测: `_decision_log` 记录每条 query 走的路径
- 路径分布统计: `get_path_distribution()` (给 Badcase 分析用)
- 0 依赖 (纯 dict + str 决策)

**测试覆盖**: 10 个 case, 10/10 通过 (含 L0 / 业务库 / Agent / RAG / Cascade 全路径)

### 7.3 多套 Prompt 模板管理 (v3.4.0-b-3)

**业界对齐**: 招行 / 微众 / 蚂蚁 2025-2026 把"一个大 Prompt"拆为"按业务类型定制的多套 Prompt 模板" (10-30 套)

**12 套业务模板** (`src/agent/prompt_templates.py`):
| ID | 名称 | 必含话术 |
|----|------|---------|
| `loan_consult` | 贷款咨询 | "年化利率" / "以审批结果为准" |
| `fraud_warning` | 反诈骗 | "请注意防范电信诈骗" / "95555" |
| `aml_check` | 反洗钱 | "根据反洗钱法律法规" |
| `card_loss` | 挂失 | "立即挂失" / "报警 110" |
| `balance_query` | 余额查询 | "请登录 App" |
| `investment_risk` | 投资理财 | "非存款" / "不保本" / "风险承受能力" |
| `privacy` | 个人信息保护 | "《个人信息保护法》" |
| `complaint` | 投诉 | "非常理解" / "深表歉意" |
| `transfer_limit` | 转账限额 | "单笔/单日/单月" |
| `human_transfer` | 转人工 | "正在为您转接" |
| `apology` | 道歉/服务异常 | "非常抱歉" |
| `general` | 通用兜底 | - |

**实现**:
- `PromptTemplateManager.build_system_prompt(intent, user_query, knowledge_context)` 一键生成完整 prompt
- 自动按 intent 前缀匹配 + 通用兜底
- 每套模板含 `system_prompt` + `post_process` 规则 + `risk_phrases` 必含话术
- 0 依赖, 可扩展 (新业务直接加)

### 7.4 v3.4.0-b vs v3.4.0 vs v3.2

| 维度 | v3.2 | v3.4.0 | v3.4.0-b |
|------|------|--------|----------|
| 知识库分类 | 1 类 (565 扁平) | 1 类 | **3 类 + 7 chunk 策略** |
| 业务数据库 | 无 | 无 | **mock 5 客户 + 3 表** |
| 路由策略 | 全走 RAG | 全走 RAG | **5 路径决策** |
| 工具意图 | 无 | 无 | **跳转接口 (v3.4.0 替代方案)** |
| Prompt 模板 | 1 个 `_build_system_prompt` | 35+ L1 模板 | **12 套业务模板** |
| 后处理 | banking_adapter | banking_adapter | **模板 + 必含话术** |
| pytest | 40 (100% pass) | 53 (100% pass) | **108 (100% pass)** |
| 新增文件 | - | - | **3 代码 + 3 测试** |

### 7.5 业界对齐 (v3.4.0-b 优势)

| 业界做法 | 本项目实现 | 备注 |
|---------|-----------|------|
| **招行小招 5 路径路由** | RouteDecisionMaker | 优先级 1-5 固定 |
| **微众 Text2SQL** | BizDBMock (订单/产品/物流) | mock 雏形 |
| **蚂蚁客服多模板** | 12 套业务模板 | 0 依赖 |
| **大厂 PM "为什么不做" 决策** | 工具意图 v3.4.0 暂不做 | 面试加分 |
| **大厂周会机制** | BadcasePool (v3.4.0-a) | 闭环 |

---

## 七、AI 产品运营能力映射（面试可讲）

| 能力 | 在项目中的体现 | 业界方法论 |
|------|---------------|-----------|
| **业务场景识别** | 银行 95555 客服场景 | L1/L2/L3 分层（招行实战） |
| **评测体系搭建** | RAGAS 4 项 + 业务 3 项 + **v3.4.0 真 LLM 600 样本** | 论文：RAGAS ArXiv:2309.15217 |
| **★ Harness 工程评测** | v3.2 三层指标 + 三大评估缺口 | CMU/Yale Survey ETCLOVG 七层架构 |
| **★ Cascade 路由 (v3.4.0)** | L1 模板 + L2 RAG + L3 LLM 三级路由 | Anthropic / LangGraph / AWS Bedrock Agent |
| **RAG 调优** | 4 阶段 pipeline: BM25 + Dense + MultiQuery + Rerank | RAGAS 上下文精度/召回 |
| **Agent 工程** | 端到端 Pipeline + 多轮对话 + 上下文 | function call 评测 |
| **业务转化分析** | 四象限联动诊断 | 客服中心白皮书 |
| **钱效意识** | Uplift Model ROI | 因果推断 |
| **★ Badcase 闭环 (v3.4.0)** | 标注池 + 自动定级 + 一键入 KB | 大厂 PM 周会机制 |
| **数据驱动** | P50/P95 响应时长 + Cascade 路由耗时 | SLA 监控 |

---

## 八、迭代历程

| Commit | 说明 |
|--------|------|
| c9882b5 | init project |
| 299d34f | v1.1 metrics + intent + KB |
| 48e6e3a | 400-sample dataset + generator |
| ff95e2b | eval automation |
| b4f52c6 | UTF-8 BOM fix |
| d1bf180 | intent speed optimization |
| 9e964c1 | 100% intent coverage |
| 20fd608 | v5 eval engine + dataset |
| 5f069be | intent accuracy 82.3% → 83.5% |
| **e093519** | **★ v6: 对齐 RAGAS 工业级框架** |
| **80268e0** | **★ v1: 业务四象限指标体系** |
| 85da22e | ★ 银行业 RAGAS 适配器（Adapter 模式） |
| 948a25d | 银行业务调整 PDF v2.1 |
| 2b74dbc | 面试题库 PDF v2.2（14 页合并版） |
| 735f42c | 拆分两个独立 PDF（项目复盘 6 页 + 面试题库 12 页）v2.2 |
| **(next)** | **★ v3.2 评测方案：Harness 7 层架构 + 三大评估缺口 + 项目清理（70+ 老文件回收）** |
| **6492a5f** | **★ v3.3.3 知识库 565 条 v2.0 接入代码** |
| **92163aa** | **★ v3.3.4 RAG 检索增强 + L0 词典整合** |
| **92163aa** | **★ v3.3.5 RAG 4 阶段业界 pipeline (Sparse + Dense + MultiQuery + Rerank)** |
| **(待 push)** | **★ v3.3.6 LLM 接入 (订阅 Key + api.minimaxi.com 端点)** |
| **(待 push)** | **★ v3.3.7 L0 误伤降级 + 投诉意图补全** |
| **(待 push)** | **★ v3.3.8 端到端 Pipeline 串联 (意图 + L0 + RAG + LLM 真业务流)** |
| **(待 push)** | **★ v3.4.0 Cascade 路由 (L1 模板 + L2 RAG + L3 LLM, LLM 调用率 6.83%, 节省 93.2%) + Badcase 标注池 (13 条 + 演示标注 4 条 + 入 KB 1 条)** |
| **(待 push)** | **★ v3.4.0-b 知识库分类 (3 类 + 7 chunk 策略 + 业务数据库 mock) + 5 路径路由决策器 + 12 套业务 Prompt 模板 (108 测试全过)** |

---

## 九、银行业务调整（Adapter 模式）

通用 RAGAS 框架是好的起点，但银行业是**强监管行业**，必须做业务适配。本项目用 Adapter 模式实现：

```
BaseRAGASAdapter (抽象基类 — 跨场景可复用)
        ↓ 继承
BankingComplianceMixin (银行业合规能力)
        ↓ 组合
BankingRAGASAdapter (银行业具体实现)
```

**适配思路：保留 RAGAS 4 项核心 + 增加银行业 5 项业务指标 + L0 红线层**

### 9.1 必须调整的 5 个地方

#### 调整 1: 业务分层 — 加 L0 红线层

通用版只有 L1/L2/L3 三层；银行业必须加 **L0 红线层**（监管要求 100% 转人工）：

| 层级 | 通用 | 银行业调整 |
|------|------|-----------|
| **L0 红线** | 无 | **新增**：反洗钱/大额可疑/反诈骗（必须转人工） |
| L1 简单 | 60% / FCR 90% | 60% / FCR 95%（银行标准更严） |
| L2 中等 | 30% / FCR 75% | 30% / FCR 80% |
| L3 复杂 | 10% / FCR 50% | 10% / FCR 50% |

#### 调整 2: 敏感信息检测 — 多 4 个模式

| 模式 | 通用 | 银行增加 |
|------|------|---------|
| 身份证 | ✅ | ✅ |
| 手机号 | ✅ | ✅ |
| **银行卡号** | ❌ | ✅ 16-19 位 |
| **CVV** | ❌ | ✅ |
| **验证码** | ❌ | ✅ |
| **明文密码** | ✅ | ✅ |

#### 调整 3: 监管话术合规 — 银行业独有

不同场景必须说指定的合规话术：
- **贷款场景**：必须说"年化利率"
- **反诈骗场景**：必须说"请注意防范电信诈骗，我行不会通过电话/短信索要您的密码"
- **AML 场景**：必须说"根据反洗钱法律法规"
- **个人信息**：必须说"我行严格遵守《个人信息保护法》"

#### 调整 4: 反洗钱/反诈骗关键词 — 银行业独有

L0 红线关键词：
- **反洗钱**：分多笔、拆单、每次不到 5 万、兑换外币
- **反诈骗**：被骗、盗刷、账户冻结、给陌生人转
- **越权**：帮 XX 查账户（代查他人）

触发即 100% 转人工 + 同步上报合规。

#### 调整 5: 钱效模型 — 加合规成本

```
通用版 ROI = 净节省 / 投入

银行业 ROI = (节省人力 - AI 投入 - 合规成本) / (AI 投入 + 合规成本)
           ↑
合规成本 = 等保三级测评（30-50万）+ 银保监审计（10-20万/年）
        + 数据本地化部署（+30% 服务器成本）+ 人工复核
```

### 9.2 业界最佳实践参考

| 银行/案例 | 关键做法 |
|----------|----------|
| **微众银行** | 联邦学习 + 知识图谱，0.8% 坏账率，AI 客服替代 83% 尽调，单户成本 47 元 |
| **招商银行** | 人机结合（智能机器人辅助人工），「小招」智能语音服务全面 |
| **建设银行** | 数字人「班克」+ 语音唤醒 |
| **光大银行** | 客服形式最全面（含视频客服、手语客服） |
| **21世纪测评** | 招行/交行/光大三家综合得分最高 |

### 9.3 4 大趋势（21世纪经济报道）

1. **精细化运营与普适化** — 适老化改造、无障碍体验
2. **客户个性化服务** — 千人千面的常用功能/活动
3. **人机结合** — 智能客服辅助客户经理
4. **数字人** — 增强智能客服交互体验

### 9.4 完整文件

| 文件 | 说明 |
|------|------|
| `src/eval/banking_adapter.py` | 716 行，银行业 RAGAS 适配器（Adapter 模式） |

---

## 十、面试用 STAR 法则

**情境（S）**：银行业进入 AI Agent 时代，需要评测 AI 客服的真实业务价值；同时业界正在从"模型能力"转向"Harness 工程"，传统的"只看最终输出"评测无法定位 Agent 真实失效的根因。

**任务（T）**：搭建可对标业界标准（RAGAS + Harness 7 层架构）的 AI 客服评测 + 业务转化漏斗分析体系。

**行动（A）**：
1. 引入 RAGAS 4 大核心指标（faithfulness/answer_relevancy/context_precision/context_recall）
2. 设计业务四象限（CSAT/FCR/转人工率/响应时长）分层评估
3. 实现 L1/L2/L3 复杂度分层（招行实战）
4. 开发 Badcase 周会分析器（P0/P1/P2 自动定级 + 9 大错误分类）
5. 引入 Uplift Model 计算 ROI 和净节省
6. **★ v3.2 引入 Harness 工程搭建式评测**（评测 Agent 提示词 + 三大评估缺口 + 协同增强视角）

**结果（R）**：
- 评测体系对齐业界事实标准 RAGAS
- 业务指标体系覆盖 7 大维度
- 四象限自动诊断，无需人工肉眼看
- 钱效模型可直接给业务方汇报（ROI、净节省）
- **★ Harness 评测方案 v3.2** —— 23 页，纳入 CMU/Yale Survey 学术框架，三层指标（L1/L2/L3）+ ETCLOVG 七层映射，3 大评估缺口覆盖（安全/成本/模型-Harness 分离）

---

## 十一、相关参考

- [RAGAS GitHub](https://github.com/explodinggradients/ragas) - 4k+ stars
- [RAGAS Paper](https://arxiv.org/abs/2309.15217) - ArXiv
- [DeepEval](https://github.com/confident-ai/deepeval) - CI/CD 集成
- [RAGChecker](https://github.com/amazon-science/RAGChecker) - 亚马逊细粒度诊断
- **★ [Agent Harness Engineering: A Survey](https://openreview.net/pdf?id=eONq7FdiHa)** - CMU/Yale/Amazon 综述（ETCLOVG 七层架构）
- **★ [Agent Systems with Harness Engineering](https://openreview.net/pdf?id=nM5tDHrQsx)** - 62 页（协同增强视角）
- **★ [awesome-agent-harness](https://github.com/Picrew/awesome-agent-harness)** - 项目样本库
- 央行《商业银行 AI 应用合规指引》2025 年 1 月
- 21世纪经济报道：手机银行智能客服测评 2023-11
- 微众银行《联邦大模型技术白皮书》2024

---

## License

MIT

---

**更新时间**：2026-06-12
**v3.4.0-b 新增** (待 push)：知识库 3 类分类 (doc_kb 280 / faq_kb 285 / biz_db 5客户 3表) + 7 种 Chunking 策略 + 5 路径路由决策器 (L0_HUMAN / BIZ_DB_API / AGENT_TOOL / RAG_KB / CASCADE_TEMPLATE) + 12 套业务 Prompt 模板 (贷款/反诈/反洗钱/挂失/余额/投资/隐私/投诉/限额/转人工/道歉/通用) + pytest 108/108 通过
**v3.4.0** (待 push)：Cascade 路由 (L1 模板 + L2 RAG + L3 LLM) + 真 LLM 600 样本评测 (意图 83% / L0 100% / RAG 98.75% / LLM 调用率 6.83%) + Badcase 标注池 (13 条 + 演示标注 4 条 + 一键入 KB)
**v3.3.6-v3.3.8** (待 push)：LLM 接入 (订阅 Key + api.minimaxi.com 端点) + L0 误伤降级 + 端到端 Pipeline 串联
