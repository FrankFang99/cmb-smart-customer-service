# 招商银行智能客服 (CMB Smart Customer Service)

> 基于 LangChain + DeepSeek 的银行客服 AI 系统
> **抽象 RAGAS 工业级框架 + 银行业务调整（Adapter 模式）+ Harness 工程搭建式评测**

[![评测](https://img.shields.io/badge/RAGAS-4%E5%A4%A7%E6%8C%87%E6%A0%87-blue)]()
[![业务](https://img.shields.io/badge/业务-FCR%2FCSAT%2F钱效-green)]()
[![方法论](https://img.shields.io/badge/方法论-业界前沿-orange)]()
[![评测](https://img.shields.io/badge/%E8%AF%84%E6%B5%8B-v3.2_Harness-orange)]()

---

## 一、项目定位

本项目是面向 **AI 产品运营** 求职的作品集，对齐业界（2025-2026）最前沿的方法论：

| 维度 | 业界事实标准 | 本项目实现 |
|------|--------------|-----------|
| **评测框架** | RAGAS（GitHub 4k+ stars） | ✅ `eval_runner_v6.py` 4 大核心指标 + 3 项业务扩展 |
| **业务指标** | 客服中心四象限（CSAT/FCR/转人工率/响应时长） | ✅ `business_metrics.py` 7 大指标 + 分层 + 钱效 |
| **分层策略** | L1/L2/L3 复杂度分层 | ✅ 招行实战分层映射 |
| **Badcase 管理** | P0/P1/P2 自动定级 | ✅ `BadcaseAnalyzer` 24h/3d/1w 响应 |
| **钱效模型** | Uplift Model | ✅ ROI + 净节省 + 单次成本对比 |
| **★ Harness 工程评测** | CMU/Yale Survey ETCLOVG 七层架构 | ✅ v3.2 评测方案：L1/L2/L3 + 三大评估缺口 + 协同增强视角 |

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
            KB[知识库<br/>40条业务知识]
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

### 3.5 RAG 知识库

**文件**：`src/rag/knowledge_base.py`

- 40 条业务知识
- 6 大 category（query / transaction / consult / marketing / risk / info）
- Chroma + BM25 混合检索

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
│   └── 银行业务知识库_v1.0.md
├── knowledge_base/                        # 银行业务知识库
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

## 七、AI 产品运营能力映射（面试可讲）

| 能力 | 在项目中的体现 | 业界方法论 |
|------|---------------|-----------|
| **业务场景识别** | 银行 95555 客服场景 | L1/L2/L3 分层（招行实战） |
| **评测体系搭建** | RAGAS 4 项 + 业务 3 项 | 论文：RAGAS ArXiv:2309.15217 |
| **★ Harness 工程评测** | v3.2 三层指标 + 三大评估缺口 | CMU/Yale Survey ETCLOVG 七层架构 |
| **RAG 调优** | Chroma + BM25 混合 | RAGAS 上下文精度/召回 |
| **Agent 工程** | LangChain Agent + 工具 | function call 评测 |
| **业务转化分析** | 四象限联动诊断 | 客服中心白皮书 |
| **钱效意识** | Uplift Model ROI | 因果推断 |
| **Badcase 管理** | P0/P1/P2 自动定级 + 9 大错误分类（含 v3.2 新增） | 大厂周会机制 |
| **数据驱动** | P50/P95 响应时长 | SLA 监控 |

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

**更新时间**：2026-06-09
**v3.2 新增**：Harness 工程搭建式评测方案（对齐 CMU/Yale Survey ETCLOVG 七层架构 + 三大评估缺口 + 协同增强视角）+ 项目清理（70+ 调试/老旧文件回收）
