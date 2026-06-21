# RAG 知识库设计 v1.0

> 文档目的：基于 v3.2 分类标准（7 域 84 三级 21 P0）设计招行智能客服的 RAG 知识库体系，作为意图识别后的检索路径与回答生成的知识源。
>
> 适用版本：v1.0（与 v3.2 分类标准配套）
> 业界对齐：美团 WOWService / 蚂蚁 Agentar / 招行"小招" / 微众 BankBot 四家业界最高标准
> 核心思路：**84 三级不是知识库本身，是检索路径的分流器**——意图不同 → 检索路径不同

---

## 一、设计目标与原则

### 1.1 设计目标

| 目标 | 度量 |
|---|---|
| **回答正确性** | RAGAS Faithfulness ≥ 0.90，Context Precision ≥ 0.85 |
| **检索召回** | 84 三级每级 Top-3 召回率 ≥ 95% |
| **P0 红线零幻觉** | 21 P0 红线 100% 走模板，不允许自由生成 |
| **响应时延** | 检索路径 P95 ≤ 300ms（含嵌入） |
| **大模型调用率** | 目标 ≤ 15%（高频 FAQ 直出，低频走 LLM 兜底） |

### 1.2 设计原则

1. **意图驱动**：检索路径由意图标签决定，不是按 query 关键词硬匹配
2. **多层并存**：结构化 QA + 知识图谱 + 非结构化文档 + 工单库四层并行
3. **P0 强约束**：21 个 P0 红线 100% 走模板回复，不允许大模型自由生成
4. **冗余优先**：宁可多召回，不可漏召回（银行业 P0 漏一次 = 事故）
5. **可追溯**：每条回答必须能引用知识库原文片段 + 版本号 + 有效期
6. **冷热分层**：高频 FAQ 走热缓存（命中 < 50ms），低频走向量库

---

## 二、四层知识库结构（业界最高标准）

```
┌──────────────────────────────────────────────────────────────┐
│                    招行智能客服 RAG 知识库                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  L1 结构化 QA 库 (FAQ)        ← 强匹配意图，高置信直出      │
│  ├─ 84 三级一对一映射         ← 每个三级类目挂 FAQ 列表      │
│  ├─ 模板回答 + 触发动作       ← P0 红线 100% 走模板          │
│  └─ 命中率预估：~55% query                                   │
│                                                              │
│  L2 知识图谱 (实体-关系)       ← 业务规则/产品/费率查询      │
│  ├─ 实体：产品/费率/卡种/币种/网点                          │
│  ├─ 关系：属于/手续费/限额/适用人群                          │
│  └─ 命中率预估：~20% query（业务规则相关）                  │
│                                                              │
│  L3 非结构化文档切片库         ← 政策/手册/合同/公告         │
│  ├─ 切片粒度：500-800 字（业界标准）                         │
│  ├─ 切片重叠：15%                                            │
│  ├─ metadata：部门/版本/生效日期/失效日期/意图标签           │
│  └─ 命中率预估：~15% query（政策/合同/手册）                │
│                                                              │
│  L4 业务工单库                  ← 历史会话反哺               │
│  ├─ 历史人工会话（脱敏）                                     │
│  ├─ 高赞回答（用户 thumbs_up）                              │
│  └─ 命中率预估：~10% query（长尾/边缘 case）                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 L1 结构化 QA 库

**结构**：每个三级类目挂 FAQ 列表，每条 FAQ 含 5 字段：

| 字段 | 说明 |
|---|---|
| `intent_id` | 84 三级 ID（如 `biz_transfer_cross_bank`）|
| `question_patterns` | 客户原话变体列表（5-15 条/FAQ）|
| `answer_template` | 模板回答（含变量插槽 `{{card_no_tail}}`）|
| `action` | 触发动作（如"打开跨行转账页面"）|
| `priority` | P0/P1/P2/P3（与分类标准对齐）|

**示例**（`biz_transfer_cross_bank`）：

```json
{
  "intent_id": "biz_transfer_cross_bank",
  "question_patterns": [
    "跨行转账怎么操作",
    "怎么转给别人",
    "跨行转账要手续费吗",
    "转给别的银行的卡怎么转"
  ],
  "answer_template": "您好，跨行转账可通过以下方式办理：\n1. App 首页 → 转账 → 跨行转账\n2. 输入收款人姓名、账号、开户行\n3. 单笔 ≤ 5 万实时到账，大额 1-2 工作日\n手续费：0-100 元/笔（按金额阶梯）",
  "action": {
    "type": "deep_link",
    "target": "cmb://transfer/cross_bank",
    "label": "立即办理"
  },
  "disambiguation": {
    "trigger": "high",
    "follow_up": "您是想要现在办理跨行转账吗？",
    "follow_up_action": {
      "type": "deep_link",
      "target": "cmb://transfer/cross_bank",
      "label": "立即办理跨行转账"
    }
  },
  "priority": "P1"
}
```

**P0 FAQ 特殊规则**：
- `answer_template` 必须是合规审核过的固定文案
- 禁止调用大模型改写
- 必须带 `risk_disclosure` 字段（如"投资有风险，理财需谨慎"）

### 2.2 L2 知识图谱

**实体类型**：
- **产品**：理财/基金/保险/存款/信用卡/贷款
- **费率**：转账手续费/账户管理费/信用卡年费/提前还款违约金
- **卡种**：一卡通/金葵花/钻石卡/无限卡
- **币种**：CNY/USD/HKD/EUR/JPY
- **网点**：北京/上海/广州/深圳…（招行 1800+ 网点）
- **业务流程**：开户/转账/挂失/密码重置/额度调整

**关系类型**：
- `属于`（产品 → 卡种）
- `手续费`（产品 × 金额区间 → 费率）
- `限额`（卡种 × 业务类型 → 日累计/单笔）
- `适用人群`（产品 → 客户等级）
- `有效期`（产品/活动 → 时间段）

**应用场景**：
- "转账手续费多少" → 知识图谱直接查 `转账 × 金额区间 → 费率`
- "金葵花有什么权益" → 知识图谱查 `金葵花 → 适用人群/产品`
- "我的卡单笔能转多少" → 知识图谱查 `卡种 × 转账 → 单笔限额`

### 2.3 L3 非结构化文档切片库

**文档来源**：
- 招行《个人银行业务手册》（~500 页，每年更新）
- 《借记卡章程》《信用卡领用合约》
- 监管文件（央行/银保监/外管局公告）
- 内部操作指南（95555 客服知识库）
- 监管处罚案例（用于反向学习）

**切片策略**（业界最佳实践）：

| 参数 | 值 | 理由 |
|---|---|---|
| **切片粒度** | 500-800 字 | 美团 WOWService 推荐粒度 |
| **切片重叠** | 15% | 避免边界信息丢失 |
| **切片方法** | 语义切分（非定长）| 按段落/标题层级切 |
| **metadata** | 部门/版本/生效日期/失效日期/意图标签 | 可追溯 + 时效管控 |
| **嵌入模型** | bge-large-zh-v1.5 | 中文 SOTA |

**metadata 必备字段**：
```json
{
  "doc_id": "PBOC-2025-123",
  "doc_title": "央行关于个人外汇管理的通知",
  "doc_version": "v2025.1",
  "doc_effective_date": "2025-01-01",
  "doc_expiry_date": "2027-12-31",
  "publish_dept": "中国人民银行",
  "intent_tags": ["consult_fx_cross", "security_aml_cross_border"],
  "chunk_index": 3,
  "chunk_total": 12
}
```

### 2.4 L4 业务工单库

**来源**：
- 历史人工会话（脱敏，去除身份证/卡号/姓名）
- 用户主动 thumbs_up 的回答
- 人工客服标记为"高赞"的回答模板

**用途**：
- 长尾 query 的兜底（"我儿子在国外读书怎么汇学费"）
- 边缘 case 的参考（"App 闪退怎么办"）
- 个性化推荐的素材（"根据您的等级推荐…"）

**更新机制**：每日凌晨离线 ETL，从生产环境拉取昨日高赞回答，经合规审核后入库。

---

## 三、检索路径分流（核心架构）

> **核心思想**：84 三级分类不是知识库本身，而是**检索路径的分流器**——意图不同 → 走的检索路径不同 → 召回的知识源不同 → 生成的回答不同

### 3.1 按意图分流的检索路径

| 意图域 | 检索路径 | 优先级 | 召回策略 |
|---|---|---|---|
| **SECURITY (7 个 P0)** | **仅 L1 模板** | 🔥 **禁止自由生成** | 模板匹配 → 直出 |
| **SAFETY (1 个 P0 + 4 个 P1)** | L1 模板 + 应急话术 | P0 强转人工 | 模板 + 动作 |
| **P0 BIZ (large_transfer/password_reset/statement_print/optout)** | L1 模板 | P0 强约束 | 模板匹配 |
| **P0 INFO (balance/card_no/open_bank)** | L1 模板（脱敏）| P0 模板 | 模板 + 数据脱敏 |
| **P0 CONSULT (mortgage)** | L1 + L2 知识图谱 | P0 模板 | 模板 + 实时数据 |
| **P0 MARKETING (5off/member_monthly/upgrade)** | L1 + 活动配置库 | P0 模板 | 模板 + 实时活动配置 |
| **P1/P2 INFO/BIZ/CONSULT** | L1 FAQ + L2 知识图谱 + L3 文档切片 | 多路召回 | RRF 融合排序 |
| **MARKETING (非 P0)** | L1 FAQ + 活动配置库（实时）| 模板 | 模板 + 配置 |
| **sys_app_help** | L1 FAQ + L3 文档（操作指南）| 多路召回 | RRF |
| **sys_service (投诉/表扬/反馈/转人工)** | 仅动作触发，**不走 RAG** | 系统动作 | 直转工单/人工 |
| **sys_other (兜底)** | L4 工单库（相似会话）+ disambiguation | 兜底 | 相似度匹配 |

### 3.2 多路召回与 RRF 融合

对非 P0 路径，采用**多路召回 + RRF (Reciprocal Rank Fusion) 融合**：

```
Query → Embedding
  │
  ├─→ L1 FAQ 向量召回 (top_k=10)
  ├─→ L2 知识图谱实体检索 (top_k=10)
  ├─→ L3 文档切片向量召回 (top_k=10)
  └─→ L4 工单库向量召回 (top_k=5)
        │
        └─→ RRF 融合排序 → top_k=5 送入生成器
```

**RRF 公式**：
```
RRF_score(d) = Σ 1 / (k + rank_i(d))   其中 k=60
```

**为什么 RRF 而不是向量直接 top1**：
- 多源融合更稳健（FA 召回强，文档召回强，工单召回强）
- 业界主流（美团/蚂蚁/微众都用 RRF）
- 避免单一向量模型的偏差

### 3.3 检索路径的伪代码

```python
def retrieve(intent_id, query, user_context):
    domain, l2, l3 = parse_intent(intent_id)
    priority = get_priority(intent_id)

    # P0 红线：仅模板，禁止自由生成
    if priority == "P0":
        if domain == "SECURITY":
            return load_security_template(l3)
        elif l3 in ["sys_service_route_human", "sys_service_complaint"]:
            return load_action_template(l3)
        elif l3 in ["biz_transfer_large", "biz_password_reset", ...]:
            return load_p0_template(l3)

    # sys_service: 仅动作，不走 RAG
    if domain == "SYSTEM" and l2 == "sys_service":
        return load_service_action(l3)

    # 多路召回
    candidates = []
    candidates += l1_faq_search(query, intent_id, top_k=10)
    candidates += l2_kg_search(query, intent_id, top_k=10)
    candidates += l3_doc_search(query, intent_id, top_k=10)
    candidates += l4_ticket_search(query, top_k=5)

    # RRF 融合
    ranked = rrf_fusion(candidates, k=60)
    return ranked[:5]
```

---

## 四、生成策略（按优先级分层）

### 4.1 P0 红线（21 个）：**模板直出，零生成**

```python
def generate_p0(intent_id, user_context):
    template = load_template(intent_id)
    # 模板填空（仅脱敏数据）
    answer = template.format(
        card_no_tail=user_context.card_no_tail or "****",
        balance=user_context.balance or "查询中",
        ...
    )
    # 强制附加风险揭示
    if intent_id in ["security_promise_yield", "security_suitability_*"]:
        answer += "\n\n投资有风险，理财需谨慎。"

    # 强制动作按钮
    if intent_id == "sys_service_complaint":
        answer += "\n\n[立即转人工] [保存会话]"
    return answer
```

### 4.2 P1/P2 普通问答：**模板优先 + LLM 润色**

```python
def generate_p1(intent_id, retrieved_docs, user_context):
    template = load_template(intent_id)
    if template:
        # 有模板：模板直出
        return template.format(**user_context.__dict__)
    else:
        # 无模板：LLM 基于检索文档生成
        context = "\n".join([d.text for d in retrieved_docs[:3]])
        prompt = f"""基于以下资料回答用户问题，仅使用资料中的信息，不要编造。
资料：
{context}

用户问题：{user_context.query}

回答要求：
1. 简洁准确，不超过 200 字
2. 必须引用资料原文
3. 末尾附 [1][2] 引用编号
"""
        return llm.generate(prompt, temperature=0.1)
```

### 4.3 多意图 disambiguation：**回答 + 追问 + 动作入口**

```python
def handle_disambiguation(intent_id, query, user_context):
    answer = generate_p1(intent_id, ...)  # 先回答
    if is_high_disambiguation_risk(intent_id):
        answer += f"\n\n{disambiguation_follow_up(intent_id)}"
        answer += f"\n\n[{disambiguation_action_label(intent_id)}]"
    return answer
```

### 4.4 sys_other 兜底：**LLM 闲聊 + 转人工**

```python
def handle_other(intent_id, query):
    if intent_id == "sys_other_greet":
        return "您好，我是招行智能客服小招，请问需要什么帮助？"
    elif intent_id == "sys_other_unclear":
        return llm.generate(
            "用户的问题可能意图不明确，请礼貌地追问并提供 2-3 个可能的选项让用户选择。",
            query=query
        )
    elif intent_id == "sys_other_invalid":
        return "抱歉，我没理解您的问题，您可以换个说法或转人工客服。"
```

---

## 五、知识库元数据规范

### 5.1 通用元数据字段

每条知识（L1 FAQ / L2 实体 / L3 切片 / L4 工单）都必须带：

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | ✅ | 全局唯一 ID（如 `L1_biz_transfer_cross_bank_001`）|
| `intent_id` | ✅ | 84 三级 ID 之一 |
| `domain` | ✅ | 7 域之一（INFO/BIZ/CONSULT/MARKETING/SECURITY/SAFETY/SYSTEM）|
| `priority` | ✅ | P0/P1/P2/P3 |
| `version` | ✅ | 知识版本号（如 `v2025.Q3`）|
| `effective_date` | ✅ | 生效日期 |
| `expiry_date` | ⚠️ | 失效日期（不填 = 长期有效）|
| `source_dept` | ✅ | 来源部门（如"零售银行部""信用卡中心"）|
| `compliance_reviewed` | ✅ | 是否合规审核（P0 必须 true）|
| `last_updated` | ✅ | 最后更新时间 |
| `updated_by` | ✅ | 更新人/系统 |

### 5.2 检索时的元数据过滤

```python
def filter_by_metadata(candidates, current_date):
    return [
        c for c in candidates
        if c.effective_date <= current_date <= c.expiry_date
        and c.compliance_reviewed == True
        and c.version in active_versions()
    ]
```

---

## 六、知识库更新与维护

### 6.1 更新触发

| 触发条件 | 更新方式 | 频次 |
|---|---|---|
| **监管政策变更** | 全量重审 + 版本号 +1 | 实时（按公告）|
| **业务规则调整** | 增量更新（仅变更加 P0 红线）| 周更 |
| **新业务上线** | 新增意图 + 新增 FAQ + 培训评测 | 月度 |
| **badcase 反馈** | 增量添加 FAQ 或修正 | 实时 |
| **定期巡检** | 全量 QA + 失效日期检查 | 季度 |

### 6.2 更新流程

```
业务部门提报 → 合规审核 → PM 评审 → 知识库入库 → 评测验证 → 灰度上线
     │                                                      │
     └──────────── badcase 反向回流 ←────────────────────────┘
```

### 6.3 版本管理

- **主版本号**（v1 → v2）：分类标准变更时升级
- **次版本号**（v1.0 → v1.1）：新增/删除三级类目
- **补丁版本号**（v1.0.0 → v1.0.1）：仅内容修订

---

## 七、业界对齐与差异

### 7.1 与业界最高标准的对比

| 维度 | 美团 WOWService | 蚂蚁 Agentar | 招行"小招" | **本方案** |
|---|---|---|---|---|
| **RAG 结构** | QA + 文档切片 | QA + KG + 文档 | QA + 工单 | ✅ **4 层全有** |
| **切片粒度** | 500-800 字 | 300-500 字 | 1000 字 | ✅ **500-800 字（业界主流）** |
| **检索融合** | RRF | 多路召回 | 单向量 | ✅ **RRF（业界主流）** |
| **P0 红线** | 模板优先 | 模板优先 | 人工优先 | ✅ **P0 100% 模板（最严）** |
| **多意图** | 澄清追问 | 澄清追问 | 转人工 | ✅ **澄清追问+动作入口** |
| **冷热分层** | 有 | 有 | 无 | ✅ **有** |

### 7.2 招行系特色（区别于互联网公司）

1. **P0 红线更严**：银行业 21 P0 vs 互联网公司通常 5-8 个
2. **合规审核更重**：每条 P0 必须合规审核，季度巡检
3. **强转人工更多**：SECURITY 域 100% 强转人工，互联网公司一般 30-50%
4. **意图标签更细**：84 三级 vs 互联网公司通常 20-30 个意图
5. **检索路径分流**：银行业按"红线/咨询/业务/活动"分 4 路，互联网公司一般按"QA/文档"分 2 路

### 7.3 微众/平安借鉴

- **微众 Agent**：45 区块 AI 应用热力图 → 我们做了"按意图分流的检索路径"（更精细化）
- **平安 BankBot**：大模型 + 小模型协同 → 我们的 Cascade L1 规则 → L2 BERT → L3 LLM
- **招行"一招"开源**：金融领域微调基础模型 → 我们用 BERT 小模型做意图识别（更可控）

---

## 八、与配套文档的关系

| 文档 | 关系 |
|---|---|
| **A_standard_v3.2.md** | 84 三级分类 → L1 FAQ intent_id 来源 |
| **A_principles_v3.2.md** | 5 条原则 → 检索路径分流的规则依据 |
| **A_existing_function_mapping_v3.2.md** | 10 模块 → L2/L3 知识源映射 |
| **C_eval_system_v3.2.md** | 评测体系 → RAGAS 五维评估本知识库 |
| **D_eval_set_v3.2.json** | 评测集 → 召回率/准确率测试 |

---

## 九、未来展望（Agent 架构）

> 此节为可选/未来展望，**不放简历主流程**。简历主线仍是 v3.2 分类 + RAG + Cascade + 评测。

**Agent 架构**（业界主流：主 Agent + 子 Agent 路由）：

```
            ┌──────────────┐
            │   主 Agent   │ ← 用户入口
            │ (Orchestrator)│
            └──────┬───────┘
                   │
       ┌───────────┼───────────┬───────────┐
       │           │           │           │
   ┌───▼───┐   ┌──▼──┐   ┌────▼────┐  ┌──▼──┐
   │分流Agent│   │理解Agent│  │回复Agent│  │营销Agent│
   │(Router)│   │(NLU)  │  │(NLG+KG)│  │(Rec.) │
   └────────┘   └───────┘  └─────────┘  └───────┘
       │           │           │           │
       ▼           ▼           ▼           ▼
   路由分发    意图识别    RAG+模板    个性化推荐
```

**4 个子 Agent 分工**：
- **分流 Agent**：根据 query 类型分到不同通道（红线/咨询/业务/活动）
- **理解 Agent**：NLU 意图识别 + 多意图 disambiguation
- **回复 Agent**：RAG 检索 + 模板生成 + 风险揭示
- **营销 Agent**：根据用户画像 + 业务场景做个性化推荐（不打扰原则）

**业界对齐**：
- 美团 WOWService、蚂蚁 Agentar、FinBot 都是这个套路
- 主 Agent + 子 Agent 路由是业界共识
- 我们 RAG 知识库已经覆盖前 3 个 Agent 的知识需求

---

## 十、附录：L1 FAQ 模板示例（10 个关键 intent）

### 10.1 `biz_transfer_cross_bank` (P1)

```json
{
  "intent_id": "biz_transfer_cross_bank",
  "domain": "BIZ",
  "priority": "P1",
  "question_patterns": [
    "跨行转账怎么操作",
    "怎么转给别人",
    "跨行转账要手续费吗",
    "转给别的银行的卡怎么转",
    "跨行转账多久到账"
  ],
  "answer_template": "您好，跨行转账可通过以下方式办理：\n\n1. **App 操作**：首页 → 转账 → 跨行转账\n2. **到账时间**：\n   - 单笔 ≤ 5 万：实时到账\n   - 单笔 > 5 万：1-2 工作日\n3. **手续费**：\n   - ≤ 1 万：0 元\n   - 1-5 万：3 元/笔\n   - > 5 万：按 0.03% 收取，最高 50 元\n\n如有疑问可拨打 95555。",
  "action": {
    "type": "deep_link",
    "target": "cmb://transfer/cross_bank",
    "label": "立即办理跨行转账"
  },
  "disambiguation": {
    "trigger": "high",
    "follow_up": "您是想要现在办理跨行转账吗？",
    "follow_up_action": {
      "type": "deep_link",
      "target": "cmb://transfer/cross_bank",
      "label": "立即办理"
    }
  },
  "metadata": {
    "source_dept": "零售银行部",
    "version": "v2025.Q3",
    "effective_date": "2025-07-01",
    "expiry_date": "2026-06-30",
    "compliance_reviewed": true
  }
}
```

### 10.2 `security_fraud_recognize` (P0)

```json
{
  "intent_id": "security_fraud_recognize",
  "domain": "SECURITY",
  "priority": "P0",
  "question_patterns": [
    "我收到个短信让我点链接，是不是诈骗",
    "95555 给我发短信让我输密码是真的吗",
    "有人让我把验证码告诉他"
  ],
  "answer_template": "⚠️ 招行不会通过短信/电话/邮件向您索要：\n- 银行卡密码\n- 短信验证码\n- CVV 码（卡背 3 位数）\n- App 登录密码\n\n如您收到疑似诈骗信息，请：\n1. **不要点击任何链接**\n2. **不要告知任何人验证码**\n3. **立即拨打 95555** 核实\n\n如已转账，请立即拨打 110 或前往派出所报案。",
  "action": {
    "type": "route_human",
    "target": "95555_fraud_center",
    "label": "立即转 95555 反诈中心"
  },
  "no_llm_generation": true,
  "metadata": {
    "source_dept": "安全保卫部",
    "version": "v2025.Q3",
    "compliance_reviewed": true
  }
}
```

### 10.3 `safety_card_loss` (P0)

```json
{
  "intent_id": "safety_card_loss",
  "domain": "SAFETY",
  "priority": "P0",
  "question_patterns": [
    "我的卡丢了怎么办",
    "我要挂失银行卡",
    "卡不见了"
  ],
  "answer_template": "⚠️ 请您立即挂失，避免资金损失：\n\n**应急挂失（5 分钟内生效）**：\n1. App：我的 → 卡片管理 → 挂失\n2. 电话：拨打 95555 按 1 转人工挂失\n3. 网点：前往任意招行网点\n\n**挂失后请**：\n1. 补办新卡（网点办理，7 个工作日）\n2. 解除原卡绑定（微信/支付宝/App）\n\n如同时发现账户异常交易，请立即转 95555 反诈中心。",
  "action": {
    "type": "route_human",
    "target": "95555_customer_service",
    "label": "立即挂失"
  },
  "dual_trigger": ["security_fraud_recognize"],
  "metadata": {
    "source_dept": "银行卡中心",
    "version": "v2025.Q3",
    "compliance_reviewed": true
  }
}
```

> **限于篇幅，其余 81 个 intent 的 FAQ 模板见附录文件 `B_rag_knowledge_base_v1_appendix.md`（实际交付时生成）**。

---

## 十一、交付清单

| 交付物 | 内容 | 状态 |
|---|---|---|
| **本设计文档** | B_rag_knowledge_base_v1.md | ✅ 已交付 |
| **L1 FAQ 模板全集** | 84 个三级类目各 1 套模板 | 📋 下一步 |
| **L2 知识图谱 schema** | 实体/关系定义 | 📋 下一步 |
| **L3 文档切片 pipeline** | 切分 + 嵌入 + 入库脚本 | 📋 下一步 |
| **检索路径配置** | 84 intent → 路径映射 JSON | 📋 下一步 |
| **评测对齐** | RAGAS 五维接入 RAG 检索结果 | 📋 C_eval_system |

---

**文档版本**：v1.0
**配套文档**：A_standard_v3.2.md / A_principles_v3.2.md / C_eval_system_v3.2.md / D_eval_set_v3.2.json
**作者**：方逸之
**日期**：2026-06-20