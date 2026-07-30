# Entity–Memory Graph Retrieval Improves Evidence Coverage in Long-Conversation Question Answering

**Shumao Sun**

*Affiliation to be supplied*

## Abstract

Long-term conversational question answering requires a memory system to find
relevant evidence across many temporally separated dialogue turns. We study
whether a conversation-built Entity–Memory graph improves retrieval over a
matched dense Memory control when Memory representations, query vectors,
answer generation, and evaluation are held fixed. Experiments use 1,986
question–answer rows from ten LoCoMo conversations. At the primary cutoff
top-k 25, graph retrieval increases official evidence recall from 79.7468% to
84.4842%, a 4.7374-point difference with paired-question and
conversation-cluster 95% bootstrap intervals of 3.6504–5.8425 and
3.5286–6.0124 points. The recall advantage is supported at every
preregistered cutoff from 5 to 50. In contrast, no matched cutoff establishes
an overall final-answer F1 difference. Ablations associate the recall gain
with semantic scoring, Entity fusion, chronological expansion, and speaker
links, while input and parameter studies bound these findings. A complete
cold/warm measurement records construction, indexing, retrieval, provider
usage, and storage: warm retrieval averages 0.004886 seconds per question
after all cache-sensitive stages fall to zero new provider requests, compared
with 1.5123 seconds in the cold pass. These results support a scoped retrieval
claim on the evaluated LoCoMo set. They do not establish improved answer F1,
cross-dataset generalization, official-reference parity, or state-of-the-art
performance.

## 1. Introduction

Conversational agents accumulate facts, events, preferences, and relationships
over interactions that exceed a model's usable context. Long-term memory
systems therefore need to decide what to store, how to organize it, and which
parts to retrieve for a new question. The LoCoMo benchmark makes this problem
concrete through long, multi-session conversations and questions requiring
single-hop, multi-hop, temporal, commonsense, and adversarial reasoning
[Maharana et al., 2024]. Its results also show that long context and
retrieval-augmented generation improve memory-related question answering but
do not remove the difficulty of long-range temporal and causal reasoning.

Dense retrieval is a natural control: encode each conversational Memory item,
score it against the question, and pass the highest-ranked items to the answer
model. This design is simple and scalable, but it treats Memory items as
independent. A graph can additionally represent repeated entities and
chronological adjacency, allowing retrieval to propagate through structure
that is absent from a flat index. The central empirical question is not whether
graphs can produce a higher headline score under a different pipeline, but
whether graph structure changes retrieval when the dense representations,
query vectors, context budget, answer model, and evaluator are controlled.

We evaluate an Entity–Memory graph built only from conversation content. Each
dialogue item becomes a Memory node, normalized Entities become shared nodes,
and chronological links connect neighboring Memories. At query time, Entity
matching is fused with semantic Memory similarity and chronological expansion.
Test questions are used only to form retrieval queries; questions, answers,
evidence labels, categories, predictions, and evaluator output are excluded
from graph construction.

The study makes three contributions:

1. It provides a matched all-question comparison between graph retrieval and
   dense Memory retrieval under shared Memory vectors, immutable ordered query
   vectors, answer generation, and evaluation.
2. It separates retrieval coverage from answer quality through official
   evidence recall, final-answer F1, paired-question uncertainty, and
   conversation-cluster uncertainty.
3. It tests graph components, input profiles, retrieval cutoffs, fusion
   weights, sequence scales, and cold/warm system cost under frozen,
   reproducible protocols.

The result is deliberately narrower than a general memory-system claim.
Complete graph retrieval improves evidence recall across top-k 5, 10, 25, and
50 on the evaluated ten-conversation set, but it does not establish higher
overall answer F1.

## 2. Related Work

### 2.1 Long-term conversational memory

LoCoMo introduced a human-verified benchmark of very long-term,
persona-grounded, multimodal conversations and evaluates question answering,
event summarization, and dialogue generation [Maharana et al., 2024].
LongMemEval later framed long-term assistant memory as indexing, retrieval, and
reading, and evaluates information extraction, multi-session reasoning,
temporal reasoning, knowledge updates, and abstention [Wu et al., 2025]. These
benchmarks motivate evaluating memory as a pipeline rather than attributing
all downstream behavior to the language model.

MemGPT approaches the context limit through virtual context management and
hierarchical memory tiers [Packer et al., 2023]. Our study addresses a
different question: given a fixed reader and fixed Memory representations,
does a conversation-derived graph improve evidence retrieval over a flat dense
control?

### 2.2 Graph retrieval

Graph-based retrieval can expose relations that independent text chunks omit.
HippoRAG combines knowledge graphs with Personalized PageRank to support
long-term knowledge integration and multi-hop retrieval
[Gutiérrez et al., 2024]. GRAG retrieves textual subgraphs and supplies both
textual and topological views to a generator [Hu et al., 2024]. Our graph is
smaller in scope and tailored to dialogue: shared Entity nodes link mentions
across Memories, while chronological edges preserve local sequence. The main
methodological emphasis is the matched control and the distinction between
evidence recall and generated-answer F1.

### 2.3 Dense retrieval controls

DRAGON is a dense retriever trained using diverse data augmentation
[Lin et al., 2023] and is used in the original LoCoMo RAG setup. We inspected
the pinned upstream reference but did not pass the project's official
reproduction tolerance. A local raw-DRAGON condition is therefore retained
only as a diagnostic and is excluded from controlled or inferential claims.
The formal comparison in this paper is instead internal and matched: dense
Memory retrieval is compared with graph retrieval using identical Memory and
query-vector artifacts.

## 3. Method

### 3.1 Conversation-only graph construction

For each conversation, the constructor consumes session timestamps, dialogue
identifiers, speaker names, dialogue text, and image captions. Each normalized
dialogue item becomes a Memory node. A `gpt-3.5-turbo` extractor at temperature
0.3 identifies Entities from the conversation text. Entity strings are
normalized, deduplicated case-insensitively, and connected to every Memory in
which they occur. Deterministic speaker links add the dialogue speaker as an
Entity. Adjacent Memory nodes are connected in chronological order, including
the declared tie-breaking and fallback rules for session ordering.

The complete ten-conversation graph contains 5,882 Memory nodes. Graph
construction does not consume QA questions, gold answers, evidence
annotations, category labels, judge outputs, previous predictions, or
question-driven ledgers. This separation prevents test questions from shaping
the stored memory structure.

### 3.2 Retrieval

At test time, the question is used for two retrieval-only signals. First, a
question-Entity extractor produces normalized keys for matching Entity nodes.
Second, the question retrieves its vector from a complete, immutable
`text-embedding-3-small` artifact. The artifact is bound to the dataset hash,
ordered question digests, model, role, vector dimension, normalization, and
artifact SHA-256; formal retrieval fails on any cache miss and makes no live
query-embedding request.

For Memory \(m\), the primary condition combines Entity relevance
\(s_e(m)\) and signed semantic similarity \(s_s(m)\):

\[
s(m) = 0.30\,s_e(m) + 0.70\,s_s(m).
\]

Entity candidates must reach a relative-score threshold of 0.5, with at most
20 matches retained per query key. Speaker-only matches are multiplied by
0.25, and Entity contributions are degree-discounted. Chronological neighbors
are expanded at secondary scale 0.5. If the gated pool contains fewer than
the requested number of Memories, semantic full-pool retrieval fills the
remaining positions without discarding gated results. Candidates are ordered
by descending fused score and then dialogue id.

The primary context budget is top-k 25. Robustness conditions use top-k 5, 10,
and 50. The dense control ranks the same Memory representations with the same
semantic query vectors but does not use Entity matching or sequence expansion.
A dense graph-construction control, B_embed, verifies that graph construction
alone does not change dense retrieval.

### 3.3 Answer generation and evaluation

Retrieved Memory text and identifiers enter the frozen LoCoMo-aligned answer
interface. The requested answer model is `gpt-3.5-turbo`, with a system-role
prompt, temperature 0, one question per batch, and a 32-token completion
limit. The evaluation package is immutable and retains its category-specific
generation, decoding, F1, evidence-recall, rounding, and aggregation behavior.

We report two distinct outcomes. Overall F1 measures final-answer overlap under
the frozen evaluator. `recall_acc` is the official evidence-recall definition.
The repository-defined Categories 1–4 subset F1 is used only as a diagnostic
and is not called an official LoCoMo metric.

### 3.4 Statistical analysis

All formal conditions contain the same 1,986 QA rows from ten conversations.
Matched differences are estimated with 10,000 paired-question bootstrap
resamples and 10,000 resamples of whole conversations, using seed 20260727.
The conversation-cluster estimator reflects uncertainty from having only ten
conversation units. Component, input, fusion, and sequence families use Holm
step-down correction within each outcome and estimator. A difference is
treated as supported only when the preregistered evidence gate passes; failure
to reject is not interpreted as equivalence.

## 4. Experimental Design

The primary comparison holds constant the dataset and row order, Memory text,
Memory vectors, immutable ordered query vectors, answer prompt, answer model,
token budget, evaluation package, output isolation, and aggregation. The
treatment activates Entity matching, graph fusion, and chronological
expansion. B_embed must reproduce the dense control's ordered context ids for
all rows before the primary graph contrast is interpreted.

Component conditions remove sequence expansion, Entity-score fusion, or the
semantic channel. A speaker ablation removes deterministic speaker links.
Input conditions compare time-annotated and raw-text profiles. Sensitivity
families vary Entity/Semantic weights and chronological scale. Cutoff
robustness uses matched A/B pairs at top-k 5, 10, 25, and 50.

Each metric-bearing condition writes to an absent, condition-specific output
directory and records source commit, resolved configuration, model names,
artifact identities, query-cache hits and misses, prompt budgets, and graph
compliance. The vendored evaluator is verified against its SHA-256 manifest
before formal use.

## 5. Results

### 5.1 Primary matched comparison

| Condition | Retrieval | Overall F1 | `recall_acc` |
|---|---|---:|---:|
| A | Dense semantic Memory retrieval | 42.0681 | 79.7468 |
| B_embed | Dense retrieval over B Memory nodes | 42.0677 | 79.7468 |
| B | Entity–Memory fusion with sequence expansion | 42.5680 | 84.4842 |

B improves `recall_acc` over A by 4.7374 percentage points. The paired-question
95% interval is 3.6504–5.8425 points, and the conversation-cluster interval is
3.5286–6.0124 points; both two-sided p-values are 0.0002. Overall F1 changes by
0.4998 points, with paired and cluster intervals of −0.5745–1.5514 and
−0.1773–1.2711 points. The F1 difference is therefore not supported.

B_embed and A have zero ordered-context mismatches across all 1,986 rows and
identical evidence recall. Their F1 values differ by less than 0.001 percentage
points, consistent with frozen Category-5 option-order randomness rather than
a retrieval difference.

### 5.2 Cutoff robustness

| top-k | A F1 | B F1 | B−A F1 | A recall | B recall | B−A recall |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 39.9053 | 39.8264 | −0.0790 | 59.3584 | 64.1667 | +4.8083 |
| 10 | 41.7607 | 42.1412 | +0.3805 | 68.9145 | 74.4847 | +5.5702 |
| 25 | 42.0681 | 42.5680 | +0.4998 | 79.7468 | 84.4842 | +4.7374 |
| 50 | 42.0782 | 41.7832 | −0.2950 | 86.7148 | 90.3306 | +3.6159 |

At every cutoff, paired-question and conversation-cluster recall intervals are
above zero. At every cutoff, both matched F1 intervals include zero. The
robust result is therefore an evidence-coverage advantage over the tested
top-k range, not an answer-quality advantage.

### 5.3 Components, inputs, and sensitivity

Within the component family, complete B improves recall over no-sequence B by
1.6728 points and over the no-Entity-score-fusion condition by 4.7626 points
after Holm correction; neither contrast supports F1. Adding sequence expansion
after Entity gating contributes 0.4364 recall points. The semantic channel
relative to Entity-only retrieval contributes 17.4634 recall points and 5.0780
F1 points, with both outcomes supported within that family. Removing
deterministic speaker links lowers recall by 1.4822 points without a supported
F1 change.

Time annotation has no supported within-B overall effect after correction.
When both A and B use raw text, B retains a supported 4.9522-point recall
advantage without an F1 advantage. Reducing Entity/Semantic weights from
0.30/0.70 to 0.10/0.90 lowers recall by 2.3062 points after correction, whereas
0.50/0.50 is not distinguishable from the primary setting. No overall F1 or
recall contrast among sequence scales 0.25, 0.5, and 1.0 survives family
correction.

### 5.4 Cold and warm system cost

| Stage | Cold requests | Cold input/output tokens | Cold timing | Warm requests | Warm timing |
|---|---:|---:|---:|---:|---:|
| Conversation-Entity extraction | 5,873 | 3,731,393 / 425,637 | 9,792.76 s summed call time | 0 | 0.00 s |
| Memory embedding index | 591 | 214,229 / 0 | 443.38 s | 0 | 1.29 s cache load |
| Question-Entity extraction | 1,974 | 1,214,259 / 104,272 | 2,970.83 s | 0 | 0.00 s |
| Retrieval, 1,986 QA | 0 | 0 / 0 | mean 1.5123 s; p95 2.6132 s | 0 | mean 0.004886 s; p95 0.006270 s |

The warm replay makes no new provider requests in the three cache-sensitive
stages. Mean retrieval latency is 309.48 times lower. Cold and warm each cover
the same 44 ordered batches, with 1,998 reads from the immutable query artifact,
zero misses, and zero live query embeddings. The formal answer trace contains
1,986 requests, 2,744,099 input tokens, and 16,269 output tokens; because
answer generation is independent of cache warmth, the same validated trace is
attached to each state instead of being rerun.

Graphs occupy 21,689,931 bytes, Memory indexes 29,946,660 bytes, and
Entity/question caches 3,411,176 bytes. Stage wall times overlap and are not
summed as end-to-end latency. We do not report monetary cost because provider
pricing was not frozen as an experimental input.

## 6. Discussion

The experiments distinguish evidence coverage from answer quality. Entity
links, semantic scoring, and chronological expansion retrieve more annotated
evidence than the matched dense control, and the difference persists across
four context budgets. The fixed short-answer generator does not convert this
additional coverage into a supported overall F1 gain. Evaluations that report
only answer scores can therefore obscure meaningful retrieval changes, while
retrieval improvements should not be described as end-to-end quality gains.

The ablations suggest that the complete effect is distributed across the
retrieval path. The semantic channel is the largest isolated contributor, but
Entity fusion, sequence expansion, and speaker links add smaller supported
recall contributions. The raw-text comparison shows that the B-over-A recall
advantage does not depend on the tested time annotation. Sensitivity results
also discourage presenting the primary parameters as universally optimal:
one lower-Entity-weight condition harms recall, an equal-weight condition is
not distinguishable, and no tested sequence scale survives family correction.

The cold/warm result exposes an operational tradeoff. Conversation Entity
extraction and Memory embedding are substantial one-time costs, and uncached
question-Entity extraction dominates cold retrieval latency. Once the
conversation artifacts and question-Entity cache are present, the graph path
requires no new provider request before answer generation and retrieval becomes
milliseconds per question. This is relevant for repeated evaluation and
repeated queries, but it does not imply the same latency on another machine,
provider, or workload.

## 7. Limitations

First, formal evidence comes from ten conversations in one LoCoMo release.
Conversation-cluster bootstrap reflects uncertainty over these ten units but
does not establish cross-dataset generalization.

Second, no matched cutoff supports an overall final-answer F1 difference.
The contribution is retrieval coverage, not a general improvement in generated
answers. A different reader or evidence selector would constitute a new
generation protocol and requires a separately controlled study.

Third, the official DRAGON reproduction gate did not pass. The local raw
DRAGON experiment changes semantic and query artifacts and remains diagnostic.
This paper makes no official-reference or state-of-the-art claim.

Fourth, the requested answer-model name is recorded, but the provider did not
persist a separate actual-model identity in the formal snapshots. Category 5
also retains the frozen upstream unseeded option-order behavior.

Finally, system timing was measured on one machine and provider endpoint.
The warm condition assumes complete reusable graph, index, and question-Entity
artifacts. Timers overlap, and monetary cost is omitted because a price
schedule was not frozen.

## 8. Reproducibility and Responsible Use

Every formal condition records its source commit, complete resolved
configuration, dataset and artifact SHA-256 values, isolated output path,
query-cache usage, provider-token telemetry, graph-input audit, and prompt
budget. Query vectors are complete and read-only during formal retrieval.
The evaluation package is vendored and hash-verified. Statistical reports and
the final cost report have independent byte-identical reproductions.

The graph uses conversation data, including speaker names and image captions,
which can contain personal information in real deployments. Systems applying
this method outside the benchmark should establish consent, retention,
deletion, and access-control policies. The present work evaluates benchmark
retrieval and does not study privacy attacks or sensitive-memory deletion.

## 9. Conclusion

A conversation-built Entity–Memory graph improves official evidence recall
over matched dense Memory retrieval across top-k 5–50 on the evaluated
ten-conversation LoCoMo set. The controlled design attributes this result to
retrieval rather than different Memory vectors, query vectors, answer
generation, or evaluation. Component evidence associates the gain with
semantic scoring, Entity fusion, chronological expansion, and speaker links.

The same experiments do not establish higher overall final-answer F1.
Retrieval coverage and answer quality should therefore be measured and claimed
separately. The result supports a scoped graph-retrieval contribution, with
cross-dataset replication, official-reference parity, and alternative readers
left for future work.

## References

- Bernal Jiménez Gutiérrez, Yiheng Shu, Yu Gu, Michihiro Yasunaga, and Yu Su.
  2024. [HippoRAG: Neurobiologically Inspired Long-Term Memory for Large
  Language Models](https://arxiv.org/abs/2405.14831). NeurIPS 2024.
- Yuntong Hu, Zhihan Lei, Zheng Zhang, Bo Pan, Chen Ling, and Liang Zhao.
  2024. [GRAG: Graph Retrieval-Augmented
  Generation](https://arxiv.org/abs/2405.16506).
- Sheng-Chieh Lin, Akari Asai, Minghan Li, Barlas Oguz, Jimmy Lin, Yashar
  Mehdad, Wen-tau Yih, and Xilun Chen. 2023.
  [How to Train Your DRAGON: Diverse Augmentation Towards Generalizable Dense
  Retrieval](https://aclanthology.org/2023.findings-emnlp.423/). Findings of
  EMNLP 2023, 6385–6400.
- Adyasha Maharana, Dong-Ho Lee, Sergey Tulyakov, Mohit Bansal, Francesco
  Barbieri, and Yuwei Fang. 2024.
  [Evaluating Very Long-Term Conversational Memory of LLM
  Agents](https://aclanthology.org/2024.acl-long.747/). ACL 2024,
  13851–13870. https://doi.org/10.18653/v1/2024.acl-long.747
- Charles Packer, Sarah Wooders, Kevin Lin, Vivian Fang, Shishir G. Patil,
  Ion Stoica, and Joseph E. Gonzalez. 2023.
  [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560).
- Di Wu, Hongwei Wang, Wenhao Yu, Yuwei Zhang, Kai-Wei Chang, and Dong Yu.
  2025. [LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive
  Memory](https://arxiv.org/abs/2410.10813). ICLR 2025.
