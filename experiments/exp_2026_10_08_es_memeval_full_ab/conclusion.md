# ES-MemEval 发布版全量 A/B：top-25 对话证据召回

## 结论与范围

冻结现有 OpenAI 配置后，在发布版派生的全部 18 名用户、1,427 道 QA 上运行纯向量 A、图方法 B 和只用于一致性检查的 B_embed。每题返回 25 条**原始对话轮次**；没有生成回答，也没有运行 Judge。离线主指标仅统计 1,130 道非拒答且至少有一个证据 ID 与原始对话 `dia_id` 直接匹配的题目。

| 本地直接对话证据召回 | A | B | B−A | 18 用户成簇 bootstrap 95% 区间 |
|---|---:|---:|---:|---:|
| 至少命中一条，top-25 | 860/1130 = 76.11% | 883/1130 = 78.14% | +23 题，+2.04 点 | +0.81 至 +3.42 点 |
| 命中全部，top-25 | 443/1130 = 39.20% | 468/1130 = 41.42% | +25 题，+2.21 点 | +1.50 至 +3.08 点 |

主指标的逐题配对 bootstrap 区间是 +0.27 至 +3.81 点；10,000 次重采样、种子 20261008。配对结果：双方均命中 820、均未命中 207、仅 B 命中 63、仅 A 命中 40。18 名用户中，14 名主指标差值为正、1 名持平、3 名为负。B 的改进在这份数据的**本地检索指标**上成立；不能据此推断回答准确率提高。

论文写的是 1,209 道 QA，而当前官方 GitHub release 派生文件有 1,427 道。261 道拒答题和另外 36 道没有直接原始对话证据 ID 的题未进入召回分母；事件 ID 没有臆造到对话 ID 的映射。因此这不是论文官方 ES-MemEval R@25，也不能把数值直接与论文表格比较。18 名虚拟用户仍限制更广人群的外推。

## 条件和完整检索路径

| 维度 / 参数 | A：确切行为 | B：确切行为 | 差异影响 |
|---|---|---|---|
| 输入 | 相同 18 用户、9,368 对话轮次、1,427 题；图只看 `sample_id`、会话时间、说话人、`dia_id`、对话文本 | 完全相同 | 控制信息量并隔绝问答标签 |
| 图 | 9,368 个 Memory 节点，无 Entity | 9,368 Memory、15,559 Entity；`MENTIONS` 与双向时序 `NEXT/PREV` | 测试实体—记忆图结构 |
| 对话抽取 | 无 | `gpt-3.5-turbo-0125` 的 `entity_instruction_guard_v2`：Who/What/When/Where/Why/How/How much；温度 0.3、最多 2,500 输出 tokens、主抽取和必要时回退各最多 3 次 | B 增加抽取成本 |
| 向量 | `text-embedding-3-small`，L2 float32；同一问题 artifact SHA `40492ac8a19e3e1849f26214f01477551e6471feb70d1a93ebf99c58965f67b9` 和 18 个 Memory 索引 | 完全相同 | 控制向量差异 |
| 查询和候选 | 问题原文向量；全 Memory 池 | 同一向量，另对问题原文抽取实体；实体 BM25 筛候选，扩展一跳时序邻居，不足 25 时稠密回填 | 候选集合可能不同 |
| 排序 | Entity 0、语义 1、无序列扩展，保留有符号余弦值 | Entity 0.3、语义 0.7、序列系数 0.5、实体相对阈值 0.5、每键最多 20 实体、Who-only 0.25、度数折扣开启；语义归一化 `none` | 冻结参数直接迁移，未按 ES 调参 |
| 输出 | top-25 原始对话 ID 和文本 | 完全相同证据单位与数量 | 可逐题配对 |
| 回答/Judge/F1 | 不运行 | 不运行 | 没有回答质量结论 |

B_embed 使用 B 图，但把排序和候选设置为 A 的 Entity 0、语义 1、全池、无序列扩展；它与 A 的 **1,427 道题逐题逐位置 top-25 ID 完全一致**。它是向量对照的完整性检查，不是新增的性能消融。三组条件的问题向量和 Memory 索引 SHA 完全相同，查询缓存缺失数及实时问题嵌入请求数均为零。两边的图输入、证据单位、top-k 和向量完全对齐；实体抽取、图结构、候选门控和融合排序是实验变量。与原论文系统仅有任务目的相似，未声称实现或指标完全对齐。

本实验由 `prepare_full.py` 分离对话建图输入、问题检索输入和离线 gold。每轮对话成为 Memory；B 对对话文本抽取实体，进行空白/标点规范化、大小写折叠、去重合并，并把说话人或抽取实体连接到来源 Memory。序列按可解析日期排序，平局/缺失时按会话与轮次回退。ES 的 ISO 日期没有触发 LoCoMo 相对时间文字追加；此数据没有图像 caption，`use_caption=true` 没有实际增加证据。18 份图都通过实体缓存覆盖、双部图和零终止抽取失败检查；3 份既有图按身份复用。

检索由 `code/em_graph/recall/service.py:EMGraphRecall.recall` 和 `code/em_graph/recall/retrieval.py:retrieve_dialog_ids` 执行。A 做全池有符号余弦排序；B 把问题实体的 BM25、度数折扣、Who-only 抑制、一跳序列扩展与稠密分数按冻结权重融合，再返回原始对话 ID。问题向量在检索前预建并绑定数据 SHA、顺序 QA digest、模型、角色、归一化和完整 artifact SHA。最初的向量 artifact 绑定到仅问题文件，索引预检拒绝它；保留该失败快照后，`rebind_query_artifact.py` 先证明 1,427 道题的顺序及全部向量值相同，再生成正确绑定检索输入文件 SHA 的新 artifact，没有重复嵌入调用。

离线 `compare_retrieval.py` 检查三组 1,427 行全覆盖、每行 25 个不重复 ID、A/B_embed 顺序完全相同和向量/索引 SHA 一致，然后才读取 gold。只计算原始 `dia_id` 的直接证据；事件证据保持未评分。用户成簇 bootstrap 连同每个用户的全部题目重采样，逐题区间单独作为参考。Judge 未运行，本地 0/1/2 LLM-as-Judge、答案 F1、温度和回答 token 上限均不适用；本次用户明确只测召回。

## 分组和成本

| 能力 | 可评分题数 | A 至少命中 | B 至少命中 | B−A |
|---|---:|---:|---:|---:|
| 冲突检测 | 259 | 77.99% | 81.47% | +3.47 点 |
| 信息提取 | 301 | 83.06% | 83.39% | +0.33 点 |
| 时间推理 | 273 | 75.82% | 76.19% | +0.37 点 |
| 用户建模 | 297 | 67.68% | 71.72% | +4.04 点 |

能力分组只作描述，没有做多重检验校正；不能从分组差值判断实体门控或时序边的单独因果作用。新建 15 份 B 图的 provider-usage 估算 USD 3.03195；先前 3 用户两段建图合计 USD 0.65931。B 本次问题抽取 1,180 次聊天请求，估算 USD 0.46165；先前缓存的 240 次估算 USD 0.09317。完整问题 artifact 为 1,420 个不同问题、142 次嵌入请求、19,071 个 provider 记录的输入 tokens；Memory 预热新增 7,618 个唯一文本向量，但完整嵌入输入 tokens 未记录，故不报精确嵌入费用。美元数是基于 API 用量的估计，不是账单；回答与 Judge 调用为零。本次增量建图加问题抽取约 USD 3.49，复用旧缓存使它低于从零开始的总开销。

强制图约束通过：建图仅用对话、说话人、时间和 `dia_id`，排除了 QA 问题、答案、证据、能力标签、Judge、旧预测及非对话时间线/摘要；B 的问题实体抽取只用于图检索。主/回退非数据提示词 scaffold 分别为 2,410/3,193 字符，低于 5,000。没有启用超限、已知无效或有害组件，也没有针对 ES 增删提示词。A、B_embed、B 的结果目录启动时均不存在，互不共用且无回答续跑。源基线提交 `86663536b03c8b7fb4cb3b205a81f82af4803746`；源文件逐项 SHA、完整参数、命令、环境绑定、输出及验证 SHA 见 `snapshots/v01_preflight_frozen/`、v03、v07、v10–v17 和 `result.json`。

## 执行命令与环境

工作目录：`/Users/sun/Documents/git/graph_memory/.worktree/es-memeval-qa`。API 阶段先执行 `source /Users/sun/Documents/git/graph_memory/env_gpt.sh` 与 `unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY`；`OPENAI_BASE_URL=https://api.openai.com/v1`，密钥不入快照。预备阶段的精确命令为：

```sh
python3 experiments/exp_2026_10_08_es_memeval_full_ab/prepare_full.py --source data/evo_emo_graph_qa.json --output-dir outputs/es_memeval_full_ab/data
python3 experiments/exp_2026_10_08_es_memeval_full_ab/prepare_query_embeddings.py --data-file outputs/es_memeval_full_ab/data/questions.json --embedding-model text-embedding-3-small --role context --normalization l2_float32_v1 --output outputs/es_memeval_full_ab/query_vectors.npz --report outputs/es_memeval_full_ab/preparation/query_report.json
python3 experiments/exp_2026_10_08_es_memeval_full_ab/rebind_query_artifact.py --source-artifact outputs/es_memeval_full_ab/query_vectors.npz --source-data outputs/es_memeval_full_ab/data/questions.json --target-data outputs/es_memeval_full_ab/data/retrieval_inputs.json --output outputs/es_memeval_full_ab/query_vectors_retrieval.npz --report outputs/es_memeval_full_ab/preparation/rebind_report.json
python3 experiments/exp_2026_10_08_es_memeval_full_ab/prepare_a.py --data-file outputs/es_memeval_full_ab/data/graph_inputs.json --cache-dir outputs/es_memeval_qa_compare/cache --extract-model gpt-3.5-turbo-0125 --output outputs/es_memeval_full_ab/preparation/a_graphs.json
python3 experiments/exp_2026_10_08_es_memeval_full_ab/prepare_indexes.py --data-file outputs/es_memeval_full_ab/data/retrieval_inputs.json --query-artifact outputs/es_memeval_full_ab/query_vectors_retrieval.npz --cache-dir outputs/es_memeval_qa_compare/cache --extract-model gpt-3.5-turbo-0125 --embedding-model text-embedding-3-small --output outputs/es_memeval_full_ab/preparation/memory_indexes.json
```

B 建图、三组检索及离线比较的精确命令如下。这里 `ROOT` 是上面的绝对工作目录，三个 `RESEARCH_*` 值与实际运行相同；每条完整命令及其 SHA 也分别冻结在 v03/v10/v11/v12/v16 的 `parameters.json` 中。

```sh
ROOT=/Users/sun/Documents/git/graph_memory/.worktree/es-memeval-qa
EXP=experiments/exp_2026_10_08_es_memeval_full_ab
export RESEARCH_RUN_CLASS=diagnostic
export RESEARCH_PARAMETER_SNAPSHOT=$ROOT/$EXP/snapshots/v03_b_graph_frozen/parameters.json
export RESEARCH_CONDITION_DIR=$ROOT/outputs/es_memeval_full_ab/conditions/b_graph_v01
python3 $EXP/build_b_graphs.py --run-id es1427_b_graph_v01 --parameter-snapshot "$RESEARCH_PARAMETER_SNAPSHOT" --data-file outputs/es_memeval_full_ab/data/graph_inputs.json --cache-dir outputs/es_memeval_qa_compare/cache --extract-model gpt-3.5-turbo-0125 --workers 8 --output-dir "$RESEARCH_CONDITION_DIR"
export RESEARCH_PARAMETER_SNAPSHOT=$ROOT/$EXP/snapshots/v10_a_top25_frozen/parameters.json
export RESEARCH_CONDITION_DIR=$ROOT/outputs/es_memeval_full_ab/conditions/es1427_A_top25_v01
python3 $EXP/run_retrieval.py --run-id es1427_A_top25_v01 --data-file outputs/es_memeval_full_ab/data/retrieval_inputs.json --variant A --top-k 25 --extract-model gpt-3.5-turbo-0125 --embedding-model text-embedding-3-small --query-artifact outputs/es_memeval_full_ab/query_vectors_retrieval.npz --parameter-snapshot "$RESEARCH_PARAMETER_SNAPSHOT" --cache-dir outputs/es_memeval_qa_compare/cache --output-dir "$RESEARCH_CONDITION_DIR"
export RESEARCH_PARAMETER_SNAPSHOT=$ROOT/$EXP/snapshots/v11_b_embed_top25_frozen/parameters.json
export RESEARCH_CONDITION_DIR=$ROOT/outputs/es_memeval_full_ab/conditions/es1427_B_embed_top25_v01
python3 $EXP/run_retrieval.py --run-id es1427_B_embed_top25_v01 --data-file outputs/es_memeval_full_ab/data/retrieval_inputs.json --variant B_embed --top-k 25 --extract-model gpt-3.5-turbo-0125 --embedding-model text-embedding-3-small --query-artifact outputs/es_memeval_full_ab/query_vectors_retrieval.npz --parameter-snapshot "$RESEARCH_PARAMETER_SNAPSHOT" --cache-dir outputs/es_memeval_qa_compare/cache --output-dir "$RESEARCH_CONDITION_DIR"
export RESEARCH_PARAMETER_SNAPSHOT=$ROOT/$EXP/snapshots/v12_b_top25_frozen/parameters.json
export RESEARCH_CONDITION_DIR=$ROOT/outputs/es_memeval_full_ab/conditions/es1427_B_top25_v01
python3 $EXP/run_retrieval.py --run-id es1427_B_top25_v01 --data-file outputs/es_memeval_full_ab/data/retrieval_inputs.json --variant B --top-k 25 --extract-model gpt-3.5-turbo-0125 --embedding-model text-embedding-3-small --query-artifact outputs/es_memeval_full_ab/query_vectors_retrieval.npz --parameter-snapshot "$RESEARCH_PARAMETER_SNAPSHOT" --cache-dir outputs/es_memeval_qa_compare/cache --output-dir "$RESEARCH_CONDITION_DIR"
python3 $EXP/compare_retrieval.py --a outputs/es_memeval_full_ab/conditions/es1427_A_top25_v01/result.json --b-embed outputs/es_memeval_full_ab/conditions/es1427_B_embed_top25_v01/result.json --b outputs/es_memeval_full_ab/conditions/es1427_B_top25_v01/result.json --graph-input outputs/es_memeval_full_ab/data/graph_inputs.json --gold outputs/es_memeval_full_ab/data/gold.json --output outputs/es_memeval_full_ab/comparison/paired_top25.json
```

所有文件的 SHA 与行数校验见 v08/v09/v13/v14/v15/v17。`result.json` 是小型机器可读结果，逐题大型结果留在 `outputs/es_memeval_full_ab/`。
