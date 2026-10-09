# 2026-10-09 迁移验证

全部检查通过，细项及精确命令见 validation.json、es_smoke_commands.json 和各阶段 parameters.json / command.sh。Hippo试跑快照在相邻 release_v109_hippo_smoke01/。ES新建图试跑源码及完整3题阶段配置在本快照；完整缓存重放配置在 es_replay_stages/。公开核心基线为f020e85，来源thesis为041c5cf；历史实验快照保持字节一致。

测试包含真实API建图/嵌入/检索和完整历史缓存重放，不只是导入。Hippo20话轮3题、ES20话轮3题均为non-metric diagnostic。没有新增论文得分、答案或Judge评估。ES三条件各1427题的有序ID完全复现，A/B_embed相同，零实时检索模型请求。数据split和离线类别/统计脚本实际运行通过。LoCoMo冻结评估器逐文件与原公共基线一致。

图构建输入为conversation（文本、说话人、会话时间、dia_id及已有caption），没有QA问题、答案、证据、类别、judge、历史预测或问题台账；问题只用于建图后的召回。召回经过对话构建的Memory/Entity节点；提示只用于图密度与图证据检索，脚手架小于5000字符。无答题和Judge模型。未移除或新增结果优化组件；本次是迁移路径兼容验证。LLM-as-Judge不适用；F1未新评分。测试环境是已有环境，未测试从空机器安装全部依赖。

公开发布入口及全部参数见README；验证源文件SHA见snapshots/v01_release_validation/release_source_sha256.json。新试跑输出与缓存只保留在outputs/reproduction_release_v109，未提交。
