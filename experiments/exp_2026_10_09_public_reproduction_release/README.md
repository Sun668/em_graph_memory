# v1.0.9 论文复现材料

本版本在 v1.0.8 基础上补充适配 HippoRAG 2、ES-MemEval 发布数据检索和 LoCoMo 五类问题分析。所有新增追踪文件在 `experiments/` 内；核心包及冻结评估器未改动。历史快照保留原样，其中旧机器的绝对路径是来源记录，不应直接作为新工作区的运行命令。下面的入口为当前可移植用法。根目录原有 README / SYNC_MANIFEST 记录的是 v1.0.8，新增材料以本目录为准。

## 环境和材料边界

EM-Graph / ES 入口使用仓库已有 Python 环境（本次实测 Python 3.9.6、numpy 2.0.2、openai 2.48.0；以 validation.json 的实际版本为准）。HippoRAG 要单独使用 Python >=3.10 环境，其固定上游 commit 为 `d5c8329422e0a0b834a15874545cb6a74b4f9b26`，包版本 2.0.0a5；本次使用已有 Python 3.11.15 环境运行。此测试没有声称在全新机器上安装全部依赖。上游依赖由其 pyproject.toml 声明；setup_upstream.py 可检查版本并安装。MIT 许可及版权见该实验的 UPSTREAM_LICENSE.txt；只提供适配代码，不把原方法改称本文方法。

需要自行导出 OPENAI_API_KEY 和 OPENAI_BASE_URL；不在仓库放入密钥或个人环境脚本。原实验请求地址为 https://api.openai.com/v1。数据下载、建图、嵌入、模型调用会产生独立本地文件和 API 费用。LoCoMo 小数据和既有正式 A/B 结果在原公开版本中；ES 原始文件由固定公开版本下载并校验。新增运行的完整缓存、逐题输出和日志不入 Git。历史小型结果、参数、源代码快照及来源哈希入 Git。保存这些文件并不保证 API 答案逐字一致。

## ES-MemEval 从原始数据运行

在仓库根目录运行，以下路径均相对于根目录。每次新运行使用新的输出/快照目录；脚本拒绝覆盖旧条件。Python 环境须能导入仓库现有依赖。原始数据 commit `692624208acc077b8867698c1d6fcd998dee641a`，哈希及适配身份见 prepare_release_data.py。

```sh
ES=experiments/exp_2026_10_08_es_memeval_full_ab
python "$ES/prepare_release_data.py" --output-dir outputs/es_reproduction_data
python "$ES/prepare_query_embeddings.py" --data-file outputs/es_reproduction_data/split/retrieval_inputs.json --output outputs/es_reproduction_query.npz --report outputs/es_reproduction_query_report.json
python "$ES/prepare_a.py" --data-file outputs/es_reproduction_data/split/graph_inputs.json --cache-dir outputs/es_reproduction_cache --extract-model gpt-3.5-turbo-0125 --output outputs/es_reproduction_a_graphs.json
python "$ES/prepare_indexes.py" --data-file outputs/es_reproduction_data/split/retrieval_inputs.json --query-artifact outputs/es_reproduction_query.npz --cache-dir outputs/es_reproduction_cache --extract-model gpt-3.5-turbo-0125 --embedding-model text-embedding-3-small --output outputs/es_reproduction_indexes.json
python "$ES/freeze_stage.py" --stage graph --run-id es_graph_r01 --data-file outputs/es_reproduction_data/split/graph_inputs.json --cache-dir outputs/es_reproduction_cache --output-dir outputs/es_reproduction_conditions/graph --snapshot-dir outputs/es_reproduction_snapshots/graph
sh outputs/es_reproduction_snapshots/graph/command.sh
```

随后对 A / B_embed / B 分别冻结并运行。B 的 `--prior-estimated-spend-usd` 填入已发生的候选阶段累计费用（包含前面数据嵌入及建图的适用费用），延续 8 美元停止上限；A/B_embed 检索不调用模型。不要把阶段费用人为归零后宣称累计上限有效。

```sh
python "$ES/freeze_stage.py" --stage A --run-id es_A_r01 --data-file outputs/es_reproduction_data/split/retrieval_inputs.json --query-artifact outputs/es_reproduction_query.npz --cache-dir outputs/es_reproduction_cache --output-dir outputs/es_reproduction_conditions/A --snapshot-dir outputs/es_reproduction_snapshots/A
sh outputs/es_reproduction_snapshots/A/command.sh
python "$ES/freeze_stage.py" --stage B_embed --run-id es_B_embed_r01 --data-file outputs/es_reproduction_data/split/retrieval_inputs.json --query-artifact outputs/es_reproduction_query.npz --cache-dir outputs/es_reproduction_cache --output-dir outputs/es_reproduction_conditions/B_embed --snapshot-dir outputs/es_reproduction_snapshots/B_embed
sh outputs/es_reproduction_snapshots/B_embed/command.sh
# 在导出 ES_PRIOR_SPEND_USD 后执行 B；该值不得低于前面已发生的适用阶段费用。
python "$ES/freeze_stage.py" --stage B --run-id es_B_r01 --data-file outputs/es_reproduction_data/split/retrieval_inputs.json --query-artifact outputs/es_reproduction_query.npz --cache-dir outputs/es_reproduction_cache --output-dir outputs/es_reproduction_conditions/B --snapshot-dir outputs/es_reproduction_snapshots/B --prior-estimated-spend-usd "$ES_PRIOR_SPEND_USD"
sh outputs/es_reproduction_snapshots/B/command.sh
python "$ES/compare_retrieval.py" --a outputs/es_reproduction_conditions/A/result.json --b-embed outputs/es_reproduction_conditions/B_embed/result.json --b outputs/es_reproduction_conditions/B/result.json --graph-input outputs/es_reproduction_data/split/graph_inputs.json --gold outputs/es_reproduction_data/split/gold.json --output outputs/es_reproduction_comparison/result.json
```

完整发布范围为 18 用户、9368 话轮、1427 QA。可计分的直接对话证据为 1130 条；排除 261 条拒答及 36 条没有直接话轮证据的其他条目。这里只做适配的本地检索比较，不生成答案、不运行 Judge，不声称官方 ES-MemEval 问答指标。索引与问题向量使用 text-embedding-3-small、context 角色、1536 维、l2_float32_v1；完整问题向量先冻结，检索时只读。

## HippoRAG 2

```sh
HIPPO=experiments/exp_2026_10_08_locomo_hipporag2
python "$HIPPO/setup_upstream.py" --upstream outputs/hipporag_upstream
python3.11 -m venv outputs/hipporag_venv
python "$HIPPO/setup_upstream.py" --upstream outputs/hipporag_upstream --python outputs/hipporag_venv/bin/python
python "$HIPPO/prepare_data.py" --output-dir outputs/locomo_hipporag2/data
python "$HIPPO/freeze_condition.py" --user-id conv-26 --mode pilot --run-id hippo_pilot_r01 --max-chat-attempts 80
sh "$HIPPO/snapshots/hippo_pilot_r01/command.sh"
```

pilot 仅 20 话轮和 3 问题，是 non-metric diagnostic。全量时用 --mode full，为每个 sample_id 单独冻结/运行，正式历史 run_id 命名见 snapshots；新工作区可用 --snapshot-root / --output-root / --data-dir / --upstream / --python 指定路径，compare_results.py 相应接受 --snapshot-root / --conditions-root / --data-dir / --formal-root / --output。每个会话一份原始话轮 Chunk，dia_id 回映到证据 ID；建图排除 QA，问题文件在建图后加载。模型 gpt-3.5-turbo-0125，温度0，NER 2048 token、三元组4096 token、线程4、最大重试2；链接5、PageRank 阻尼0.5、段落权重0.05、top-k25；fact-filter 使用上游前2个示例。无答案和 Judge 调用。不是原论文结果的严格复现，也不把此配置与本方法的模型成本/查询向量宣称完全受控匹配。

## 五类问题及实际运行测试

```sh
python experiments/exp_2026_09_15_icaart_category_analysis/analyze_categories.py --artifact-root . --output outputs/categories_reproduction
# 小规模端到端 API 测试；新建图、问题与记忆向量、A/B_embed/B，均不评分。
python experiments/exp_2026_10_09_public_reproduction_release/run_small_smoke.py --data-dir outputs/es_reproduction_data/split --output-dir outputs/es_smoke_r01
# 如另有历史完整缓存及逐题归档，可离线重放。使用缓存副本。
python experiments/exp_2026_10_09_public_reproduction_release/verify_cache_replay.py --artifact-root outputs/es_history --cache-dir outputs/es_history_cache_copy --output-dir outputs/es_replay_r01
```

类别分析只读已冻结的1986条正式 LoCoMo逐题结果，核对预测及 stats 哈希，不修改评估器、不重新生成答案。结果表中的 Categories 1–4 subset F1 是仓库定义的子集均值，不能称为官方单独指标。

## 迁移差异与证据

| 维度 / 参数 | 原研究分支 | 本公开版本 | 影响与验证 |
|---|---|---|---|
| 来源 | thesis 041c5cf；ES 原运行8666353 | main基线f020e85 + 本次experiments新增 | 原快照完整保留；source_manifest记录复制前身份 |
| ES 核心召回 | retrieval v4，fill_to_top_k=True | retrieval v3，始终补齐 | 默认行为功能相同；3条件共4281行返回的有序证据逐行完全一致 |
| ES 图/索引身份 | conversation-only Entity–Memory；A Memory-only | 同一图profile及缓存身份 | 18用户全量实际重放，A/B_embed有序相等，问题向量零miss/零实时调用 |
| 权重与筛选 | Entity0.3、semantic0.7、sequence0.5、阈值0.5、每键20、Who0.25、degree_discount=True，top25 | 相同；freeze_stage沿用历史模板 | 未调参；只迁移路径，不能据此生成新的泛化或准确率主张 |
| 模型与抽取 | GPT3.5-0125，温度0.3，2500 token；主/回退各3次，guard_v2 | 相同 | 新建小图和检索另做实时 smoke；模板原快照不覆盖 |
| 问题向量 | SHA40492ac8…；1427条、1420唯一问句 | 完整重放使用同一artifact | Memory及问题向量的身份均保存，禁止检索期间补写 |
| 冻结评估器 | 当前LoCoMo官方prompt/scoring及manifest | 未编辑；仅离线读已保存结果 | 无新回答/F1运行；不能因迁移把旧评估边界扩张 |
| 机器路径 | 固定旧工作区绝对路径 | 显式路径参数、从当前位置生成新快照命令 | 原历史结果不失效；新的API输出要重新建目录并单独审计 |

精确一致项为历史快照内容、数据适配哈希、完整重放的有序证据、A/B_embed控制和未编辑评估器；核心v3/v4默认补齐属于功能一致，源码版本不同。上游API、随机答案、全新缓存数值不能由本次测试证明逐字/逐位一致。本次已执行的测试见 validation.json / conclusion.md，属于迁移验证，论文数字保持原冻结实验。代码可运行与论文结论得到新的统计支持是两件事。
