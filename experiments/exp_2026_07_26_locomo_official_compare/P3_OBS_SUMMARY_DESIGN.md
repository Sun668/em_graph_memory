# P3 详细说明：自建 Observation-RAG / Summary-RAG

Last updated: 2026-07-26

本文回答三件事：

1. **对比逻辑从哪来**（LoCoMo 论文 Table 3）
2. **为什么要“重新生成”**（不能直接拿数据集字段当“我们的系统”）
3. **具体要做什么、最后比什么、什么算成功**

---

## 1. 第一性原理

LoCoMo Table 3 不是在比“哪个模型更聪明”，而是在比：

> **把同一段超长对话，压成哪种可检索记忆单元后，再用同一 reader 答题，效果更好？**

记忆单元 = Retrieval Unit。论文固定了：

- Retriever：DRAGON（论文实现）
- Reader：gpt-3.5-turbo + 短答 QA prompt
- 指标：token-F1（答题）+ R@k（检索是否捞到相关证据）

然后只改一件事：**库里存什么**。

```
同一对话
   │
   ├─→ Dialog 库（原始 turn）      → 检索 top-k → gpt-3.5 → F1 / R@k
   ├─→ Observation 库（人物断言） → 检索 top-k → gpt-3.5 → F1 / R@k
   └─→ Summary 库（session 摘要） → 检索 top-k → gpt-3.5 → F1 / R@k
```

这就是 Table 3 的对比逻辑来源。  
P3 要做的，是把这套逻辑搬到**我们自己的流水线**里，而不是只引用论文数字。

---

## 2. 对比逻辑来自哪里（论文坐标）

### 2.1 论文位置

- 论文：Maharana et al., *Evaluating Very Long-Term Conversational Memory of LLM Agents* (LoCoMo)
- **Table 2**：不检索，靠长/短上下文直接答（F1 only）
- **Table 3**：RAG，三种 Retrieval Unit × 多个 top-k（F1 + R@k）

Table 3 的三行：

| Retrieval Unit | 存什么 | 论文动机 |
|---|---|---|
| **Dialog** | 对话 history 的 turn | 最贴近原始证据；噪声大、指代多 |
| **Observation** | 关于 speaker 的 assertions（事实断言） | 信息密度高，接近可答事实 |
| **Summary** | session-level summaries | 覆盖广、细节粗 |

论文结论（简化）：

- Observation 往往 **F1 最高**（他们最好约 43.3 @ top-5）
- Dialog 在较大 k 时 **R@k 更高**（@25 R≈76.7）
- Summary **R 可以很高、F1 偏低**（摘要丢细节）

### 2.2 我们已经完成的对照（P0+P1）

我们已完成的是 **Dialog 族** 对照：

| 我们 | 论文 Dialog |
|---|---|
| Entity→Memory 检索 dialog turns | DRAGON 检索 dialog |
| recall_acc@25 = 82.14 | R@25 = 76.7 |
| gpt-3.5 F1@25 = 46.18 | F1@25 = 41.0 |

这证明：**在 Dialog 形态上，我们的检索+同一 reader 已超过论文 Dialog 行，并超过论文 Obs 最好 F1 数字。**

但这**没有**回答：

> 若我们也用 Observation / Summary 形态，会不会比我们自己的 Dialog 更好？

P3 就是为回答这个问题。

---

## 3. 为什么要“重新生成”？

### 3.1 数据集里其实已经有 Obs / Summary

`data/locomo10.json` 每个 sample 含：

- `observation`：按 session、按 speaker 的断言列表，且常带 dialog id（如 `D1:3`）
- `session_summary`：每个 session 一段摘要

这些字段来自 LoCoMo **造数据流水线**（agent 写 observation / summary，用于生成长对话），不是你们 runtime 记忆系统从纯对话“学出来”的。

### 3.2 两种用法，必须分开标

```
路径 A — Oracle / 数据附带（可做，但要打标签）
├── 直接索引 locomo10 的 observation / session_summary
├── 意义：上界 / 复现论文设定的近似
└── 不能宣传成“我们的记忆系统能力”

路径 B — Self-build（P3 正名含义）
├── 只用 conversation（dialogs + captions + speakers + session time）
├── 自己抽 observation / 自己写 summary
├── 再建检索库 → 同一 gpt-3.5 答题
└── 这才是“我们的 Obs-RAG / Summary-RAG”
```

**“重新生成”= 走路径 B**，避免把造数据时的副产品当成自己的记忆系统。

### 3.3 和仓库强制约束的关系

AGENTS.md 要求：

- 图/记忆构造只能用 conversation
- 不能用 QA、evidence 标注、judge、category 等

数据集里的 `observation` / `session_summary`：

- 不是 QA 泄漏，但是 **生成期记忆产物**
- 用作系统主结果 → 合规叙事弱（像开卷抄参考答案结构）
- 用作 **oracle 上界对照** → 可以，必须写明

P3 推荐设计：

1. **主实验**：self-build Obs / Summary（conversation-only）
2. **可选对照**：dataset oracle Obs / Summary（明确标 `oracle_dataset_fields`）

---

## 4. P3 最后到底对比什么？

### 4.1 主对比（必须）

**同一数据集、同一 QA、同一 reader、同一 F1/recall 口径下的记忆形态消融：**

| ID | 系统 | 检索单元 | 证据来源 |
|---|---|---|---|
| D | Entity→Memory Dialog（已有，P1） | dialog turns | 自建图检索 |
| O_self | Self-build Observation-RAG | observation 句子 | 自对话抽取 |
| S_self | Self-build Summary-RAG | session summary | 自对话摘要 |

固定：

- Reader：**gpt-3.5-turbo**
- Prompt：LoCoMo 短答 QA（与 P1 相同）
- 主指标：**Overall token-F1（含 cat5）**
- 辅指标：ex-cat5 F1、按类 F1、以及该形态下的 R@k / hit@k（定义见下）

要回答的问题：

```
O_self 或 S_self 的 F1 是否 > D（46.18）？
├── 是 → 说明换记忆形态有增益，值得并入主线或做混合
└── 否 → 说明当前 Dialog 族已够用；Obs/Summary 不必晋升
```

### 4.2 次对比（可选，解释用）

| 对比 | 含义 |
|---|---|
| O_self vs 论文 Obs F1 43.3 | 我们的自建 Obs 是否接近论文 Obs 行 |
| S_self vs 论文 Summary | 是否复现“高 R、低 F1”规律 |
| O_oracle vs O_self | 抽取质量 gap（上界 − 自建） |
| O/S vs D 的按类差异 | 谁救 Open-domain / Temporal / Adv |

### 4.3 明确不对比的东西

- 不拿 Mem0 J-score 混进这张表
- 不要求复现 DRAGON；可用现有 embedding/BM25，但报告里写清
- 不做 Event Summarization / 多模态生成（那是论文别的表）

---

## 5. 具体要做什么（可执行拆解）

### 5.0 实验落点

建议仍在本目录或子目录推进，例如：

- `experiments/exp_2026_07_26_locomo_official_compare/` 下增加 P3 runners + `snapshots/v03_…`

大文件进 `outputs/em_graph/`。

### 5.1 Observation 自建流水线

**输入（仅 conversation）**

- 每个 dialog turn：speaker、text、date_time、可选 blip caption
- 禁止：`qa`、`evidence`、`category`、judge、以及（主实验中）数据集 `observation` 字段

**抽取单位**

- 一条 observation ≈ 一句关于某 speaker 的断言  
  例：`Caroline attended an LGBTQ support group.`
- 建议附 metadata：`speaker`、`source_dia_ids`（从对话可追溯）、`session_id`
- `source_dia_ids` 只用于分析/审计，**主检索应对 observation 文本本身**（对齐论文 Observation 行）

**抽取方式（任选，需记录）**

1. LLM prompt：逐 session 或逐 turn 窗口抽 assertions（注意 prompt ≤ 5000 scaffold）
2. 规则/启发式：仅作弱基线

**建库与检索**

- 索引：observation 文本 embedding（可用 doubao 或 text-embedding-3-small，写清）
- 可选：BM25 on observation text
- Query：问题文本 → top-k observations
- 答题上下文：把 top-k observation 拼进 prompt（不再拼 dialog，或做消融 “Obs-only vs Obs→expand dialog”）

**推荐主设定（对齐论文精神）**

- **Obs-only context** 给 gpt-3.5（纯 Observation-RAG）
- k ∈ {5, 10, 25}（论文 Obs 也报这些）

### 5.2 Summary 自建流水线

**输入**：同一 conversation-only

**摘要单位**

- 每个 `session_i` → 一段 `session_i_summary`（多句可，但一个检索单元）

**抽取方式**

- LLM：给定该 session 全部 turns（+ date），生成摘要
- 禁止用数据集 `session_summary` 作为主系统输出

**检索与答题**

- 索引 session summary 文本
- top-k summaries → gpt-3.5
- 论文 Summary 的 R@k 定义是“是否捞到相关 session 的 summary”；我们若报 R，应对齐：  
  gold evidence 的 session 是否被 top-k summary 覆盖  
  （不要和 Dialog 的 dia_id recall_acc 混用同一公式不说明）

### 5.3 统一答题与指标

对 D / O_self / S_self：

1. 同一 all-10 QA
2. 同一 gpt-3.5-turbo + 同一短答 prompt（复制 P1）
3. 报告：

| 指标 | Dialog | Obs | Summary |
|---|---|---|---|
| token-F1 Overall | 已有 46.18 | ? | ? |
| token-F1 by cat | 已有 | ? | ? |
| 形态内检索指标 | recall_acc@k (dia) | R@k (obs 或 mapped) | session-cover@k |
| 平均上下文 token | 建议记 | 建议记 | 建议记 |

### 5.4 可选 Oracle 支路（一天内可做）

若想先估上界，再决定是否砸成本自建：

1. 直接用数据集 `observation` / `session_summary` 建库
2. 同一 gpt-3.5 答
3. 结果文件与 snapshot **必须**标注：

```text
oracle_dataset_fields=true
not_a_system_claim=true
```

解读：

- 若 oracle Obs F1 ≪ 46 → 即使完美 Obs 也可能不如你们 Dialog，P3 self-build 优先级下降
- 若 oracle Obs F1 ≫ 46 → 说明形态有潜力，值得 self-build 追抽取质量

---

## 6. 决策树（做完怎么判）

```
P3 结果
│
├─ O_self F1 > D(46.18) 且合规
│   → 考虑 Obs 晋升或 Dialog+Obs 混合（新实验）
│
├─ S_self F1 > D
│   → 少见；检查是否泄漏/评测口径错误
│
├─ O_self / S_self 均 < D，但 oracle Obs �口径错误
│
├─ O_self / S_self 均 < D，但 oracle Obs ≫ D
│   → 形态有价值，瓶颈在自建抽取；优化 extract prompt
│
├─ oracle Obs 也 ≤ D
│   → 停止 Obs 方向大投入；Dialog 族保持主线
│
└─ 任意结果
    → 不改写 P0/P1 已成立的「Dialog > 论文 Dialog/Obs 数字」主张
      （那是跨系统引用对照；P3 是系统内消融）
```

---

## 7. 和 Fact-memory 失败实验的关系

`exp_2026_07_26_em_fact_memory` 已在 **本地 judge / hit** 上证明：  
Mem0 风格 fact 句检索 **弱于** Entity→Memory Dialog。

P3 Observation 与 Fact 相近但不等同：

| | Fact probe（已拒） | P3 Observation |
|---|---|---|
| 目标指标 | 本地/Mem0 judge | 官方 token-F1 + 形态 R@k |
| Reader | deepseek 等 | 固定 gpt-3.5 |
| 对照 | 主要 vs Dialog judge | vs Dialog F1 + 论文 Table 3 逻辑 |
| 结论迁移 | “fact 未必更好” | 仍值得用 **官方 F1** 再验一次形态，但预期要谨慎 |

因此 P3 **不是**无视 fact 失败再盲做，而是：  
用论文同协议确认“断言库”是否在 F1 上有另一故事。优先建议 **先 oracle Obs 探一天**，再决定是否全量 self-build。

---

## 8. 建议实施顺序（降低成本）

```
Step 0  写清本文件协议（已完成）
Step 1  Oracle Obs/Summary + gpt-3.5（快，定上界）→ snapshot
Step 2  若 oracle 有希望：self-build Summary（实现简单）
Step 3  self-build Observation（成本最高）
Step 4  三表合并进 TABLE3_COMPARE.md；更新 conclusion / PLAN / TODO
```

每步都必须：

- 合规审计（conversation-only / oracle 标签）
- snapshot（runner + 命令 + 指标）
- 不把 Mem0 J-score 写进主表

---

## 9. 一句话记忆

**Table 3 的逻辑是：固定答题器，只换记忆形态。**  
P3 要自己（或先用 oracle 估上界）生成 Obs/Summary，是为了在**我们的系统内**做同样的形态消融；  
最终主对比是 **Dialog vs 自建 Obs vs 自建 Summary 的 gpt-3.5 F1**，不是再去“抄论文的库”。

---

## 10. 关联知识

- 已完成：`TABLE3_COMPARE.md`（Dialog vs 论文数字）
- 已完成：P1 gpt-3.5 F1 46.18（Dialog 族主张）
- 相关失败：`exp_2026_07_26_em_fact_memory`（fact ≠ 自动更优）
- 论文任务边界：Table 2 长上下文、Table 4 event summary、多模态生成 ≠ P3
