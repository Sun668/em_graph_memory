# Literature verification for the arXiv manuscript

Checked 2026-07-30 against primary paper or official proceedings pages.
The corresponding 20-item Zotero collection is
`Graph Memory Paper - Verified References` (`TNDVXSZ8`).

| Citation | Primary source | Claim used in the draft | Verification |
|---|---|---|---|
| Maharana et al. (2024) | [ACL Anthology](https://aclanthology.org/2024.acl-long.747/) | LoCoMo evaluates very long-term conversational memory through QA, event summarization, and multimodal dialogue generation; its QA setup includes RAG with DRAGON. | Verified from the ACL paper page and paper text. |
| Wu et al. (2025) | [arXiv 2410.10813](https://arxiv.org/abs/2410.10813) | LongMemEval evaluates five long-term memory abilities and decomposes memory design into indexing, retrieval, and reading. | Verified from the paper abstract; listed as ICLR 2025. |
| Packer et al. (2023) | [arXiv 2310.08560](https://arxiv.org/abs/2310.08560) | MemGPT uses virtual context management and hierarchical memory tiers. | Verified from the paper abstract. |
| Gutiérrez et al. (2024) | [arXiv 2405.14831](https://arxiv.org/abs/2405.14831) | HippoRAG combines an LLM, a knowledge graph, and Personalized PageRank for long-term knowledge integration and retrieval. | Verified from the paper abstract; listed as NeurIPS 2024. |
| Hu et al. (2025) | [ACL Anthology](https://aclanthology.org/2025.findings-naacl.232/) | GRAG retrieves textual subgraphs and supplies textual and topological views for generation. | Verified from the Findings of NAACL paper page and abstract. |
| Lin et al. (2023) | [ACL Anthology](https://aclanthology.org/2023.findings-emnlp.423/) | DRAGON is a dense retriever trained with diverse data augmentation. | Verified from the Findings of EMNLP paper. |
| Lewis et al. (2020) | [NeurIPS](https://proceedings.neurips.cc/paper/2020/hash/6b493230-Abstract.html) | RAG combines a parametric generator with a dense non-parametric memory. | Verified from the NeurIPS paper page. |
| Karpukhin et al. (2020) | [ACL Anthology](https://aclanthology.org/2020.emnlp-main.550/) | DPR uses a learned dual encoder to retrieve passages for open-domain QA. | Verified from the EMNLP paper page and abstract. |
| Sarthi et al. (2024) | [OpenReview](https://openreview.net/forum?id=GN921JHCRw) | RAPTOR recursively embeds, clusters, and summarizes chunks into a hierarchy used for retrieval. | Verified from the ICLR 2024 paper. |
| Qian et al. (2024) | [arXiv 2409.05591](https://arxiv.org/abs/2409.05591) | MemoRAG forms global memory with a long-range model and uses generated clues to guide retrieval. | Verified from the current arXiv abstract. The Zotero item retains an earlier title for the same arXiv identifier. |
| Park et al. (2023) | [ACM DOI](https://doi.org/10.1145/3586183.3606763) | Generative Agents stores observations, synthesizes reflections, and retrieves memories for planning. | Verified from the UIST paper page. |
| Zhong et al. (2024) | [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/29946) | MemoryBank provides conversational memory retrieval and updating with time-dependent forgetting and reinforcement. | Verified from the AAAI paper page and abstract. |
| Chhikara et al. (2025) | [arXiv 2504.19413](https://arxiv.org/abs/2504.19413) | Mem0 extracts, consolidates, and retrieves conversational information and includes a graph-memory variant. | Verified from the arXiv abstract. |
| Xu et al. (2025) | [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html) | A-Mem dynamically creates, indexes, links, and updates structured memory notes. | Verified from the NeurIPS 2025 paper page. |
| Edge et al. (2024) | [arXiv 2404.16130](https://arxiv.org/abs/2404.16130) | GraphRAG constructs a graph index and community summaries for global questions over a text corpus. | Verified from the paper abstract. |
| Guo et al. (2025) | [ACL paper](https://aclanthology.org/anthology-files/pdf/findings/2025.findings-emnlp.568.pdf) | LightRAG combines graph indexing with dual-level retrieval over entities and relations. | Verified from the Findings of EMNLP paper. |
| Banerjee et al. (2026) | [ACL Anthology](https://aclanthology.org/2026.acl-long.749/) | APEX-MEM stores temporally grounded events in a property graph and resolves evolving information during retrieval. | Verified from the ACL 2026 abstract. |
| Tang et al. (2026) | [ACL Anthology](https://aclanthology.org/2026.acl-long.1096/) | Mnemis combines similarity retrieval over a base graph with top-down selection over a semantic hierarchy. | Verified from the ACL 2026 abstract. |
| Wu et al. (2026) | [ACL Anthology](https://aclanthology.org/2026.acl-long.1600/) | GAM separates an event-progression graph from a topic-association network and applies graph-guided retrieval. | Verified from the ACL 2026 abstract. |
| Li et al. (2026) | [ACL Anthology](https://aclanthology.org/2026.findings-acl.1091/) | TiMem consolidates conversational observations into a temporal hierarchy and adapts recall to query complexity. | Verified from the Findings of ACL 2026 abstract. |

The manuscript does not claim that the local experiment reproduces DRAGON,
exceeds these systems, or is state of the art. Literature citations provide
problem positioning and method context only. Published scores are not compared
numerically because the systems change readers, graph construction, prompts,
context budgets, and metrics. All experimental numbers in the manuscript come
from the repository's frozen evidence.
