# Entity–Memory Graph Retrieval Improves Evidence Coverage in Long-Conversation Question Answering

**Shumao Sun**
*Tsinghua University*

## Abstract

Entity–Memory graph retrieval keeps dialogue turns as verbatim Memory nodes,
links repeated mentions through shared Entities, and connects adjacent
Memories with directed chronological edges. At query time the retriever moves
from Entity gating through semantic fusion and one-hop chronological recovery
to dense backfill. The path can keep a neighboring Memory that dense cosine
ranking would otherwise omit. A matched dense control
shares the Memory and query vectors, context budget, requested answer
protocol, and evaluator, isolating graph structure from changes to the
reader.

On 1,986 questions from ten LoCoMo conversations, graph retrieval raises
official evidence recall at top-k 25 from 79.7468% to 84.4842%. The recall
advantage is supported from top-k 5 to 50, while no matched cutoff supports
an overall final-answer F1 difference. Four paper-eligible requested
configurations support empirical robustness across the tested GPT-3.5 and
DeepSeek extractors on both outcomes. Embedding robustness is mixed: F1 has
no supported contrast, but recall is sensitive to the embedding artifact.
The comparison isolates a retrieval-coverage gain from graph structure. It
does not establish a final-answer F1 gain, model or embedding equivalence, or
cross-dataset generalization.

**Keywords:** long-term conversational memory; Entity–Memory graph retrieval;
evidence retrieval; LoCoMo

## 1. Introduction

Conversational agents accumulate facts, events, preferences, and relationships
over interactions that exceed a model's usable context. Long-term memory
systems must therefore decide what to store, how to organize it, and which
parts to retrieve for a new question. LoCoMo makes this problem concrete
through long, multi-session conversations and questions requiring single-hop,
multi-hop, temporal, commonsense, and adversarial reasoning [Maharana et al.,
2024]. Long-context and retrieval-augmented generation improve memory-related
question answering, but long-range temporal and causal reasoning remain
difficult.

Dense retrieval is a natural control. It encodes each conversational Memory
item, scores that item against the question, and sends the highest-ranked
items to an answer model. The design is simple and scalable, but treats
Memories as independent. A graph can represent repeated entities and
chronological adjacency, allowing retrieval to use structure absent from a
flat index. A valid comparison must distinguish that structural contribution
from changes in embeddings, context budgets, answer protocols, or evaluation.

We evaluate an Entity–Memory graph built only from conversation content. Each
dialogue item becomes a Memory node, normalized Entities become shared nodes,
and chronological links connect neighboring Memories. Entity matching is
fused with semantic Memory similarity and chronological expansion at query
time. Test questions form retrieval queries only. Questions, answers,
evidence labels, categories, predictions, and evaluator outputs are excluded
from graph construction.

The study addresses three research questions:

1. **RQ1.** When Memory nodes, ordered query vectors, answer generation, and
   evaluation are fixed, does complete graph retrieval improve evidence recall
   over matched dense retrieval, and does any retrieval gain translate into
   higher overall final-answer F1?
2. **RQ2.** Which retrieval components are associated with the observed
   difference in evidence recall?
3. **RQ3.** How robust is the graph-retrieval advantage across context cutoffs
   and input profiles, how sensitive are F1 and evidence recall to fusion and
   sequence settings and paper-eligible requested extractor/embedding
   configurations, and where are the category-level strengths and weaknesses
   concentrated?

The contributions are:

1. a formal conversation-only Entity–Memory retrieval model that separates
   graph construction from question-time retrieval;
2. an all-question matched comparison that holds Memory vectors, ordered
   query vectors, requested answer generation, and evaluation fixed while
   measuring evidence recall separately from final-answer F1; and
3. outcome-specific analyses of components, cutoffs, input profiles,
   parameters, the four paper-eligible requested configurations, descriptive
   category profiles, audited cases, and cold/warm operation that delimit
   where the retrieval difference holds and whether it reaches final-answer
   F1.

The full experiment covers the primary matched A/B comparison, structural
ablations, four context cutoffs, raw and time-annotated inputs,
fusion/sequence sensitivity, and a paper-eligible
two-requested-extractor-by-two-embedding matrix. The main pattern is
outcome-specific: graph structure improves evidence coverage, the tested
requested extractors support empirical robustness in both F1 and recall, and
the tested embeddings yield mixed robustness, with empirical F1 robustness
but supported recall differences.

## 2. Related Work

### 2.1 Why long conversations need structured retrieval

Long conversations scatter related facts across sessions, so a memory system
must preserve both semantic relevance and relations among separated turns.
Retrieval-augmented generation combines a parametric generator with retrieved
non-parametric evidence [Lewis et al., 2020], while Dense Passage Retrieval
establishes a strong flat dense-retrieval model [Karpukhin et al., 2020].
RAPTOR organizes text in a recursive retrieval tree [Sarthi et al., 2024], and
MemoRAG forms global memory and clues for downstream retrieval [Qian et al.,
2024]. Our method also adds structure above independent Memory vectors, but
retains dialogue items as answer evidence rather than replacing them with
generated summaries.

### 2.2 Long-term conversational memory

LoCoMo evaluates question answering, event summarization, and dialogue
generation over human-verified long conversations [Maharana et al., 2024].
LongMemEval later decomposes assistant memory into indexing, retrieval, and
reading [Wu et al., 2025]. Generative Agents, MemoryBank, and MemGPT introduced
persistent experience, retrieval/reflection, forgetting, and virtual memory
[Park et al., 2023; Zhong et al., 2024; Packer et al., 2023]. More recent
systems such as Mem0 and A-Mem extract, consolidate, index, and link memory
records [Chhikara et al., 2025; Xu et al., 2025]. Our narrower question is
whether a conversation-derived graph changes evidence retrieval when Memory
representations and the requested reader protocol are controlled.

### 2.3 Graph retrieval and the comparison gap

HippoRAG, GraphRAG, GRAG, and LightRAG use knowledge graphs, community
summaries, subgraphs, or dual-level entity/relation retrieval to expose
relations that independent chunks omit [Gutiérrez et al., 2024; Edge et al.,
2024; Hu et al., 2025; Guo et al., 2025]. APEX-MEM, Mnemis, GAM, and TiMem add
temporally grounded property graphs, semantic hierarchies, event progression,
or temporal consolidation to conversational memory [Banerjee et al., 2026;
Tang et al., 2026; Wu et al., 2026; Li et al., 2026].

These systems motivate graph memory but also expose an attribution problem:
system-level comparisons often change the graph, encoder, reader, prompt, and
context budget together. DRAGON, used by the original LoCoMo RAG setup, is a
dense retriever trained with diverse data augmentation [Lin et al., 2023]. We
therefore treat external systems as descriptive anchors and use an internal
matched dense control to isolate graph retrieval. This is an experimental
control choice, not a new metric.

## 3. Method

### 3.1 Task and estimands

Let a conversation be an ordered collection of Memory items
\(\mathcal{M}=\{m_1,\ldots,m_n\}\), where each item contains a dialogue id,
speaker, text, timestamp, and optional image caption. Given question \(q\), a
retriever returns ordered context \(R_k(q)\subseteq\mathcal{M}\) with
\(|R_k(q)|=k\).

Graph construction is conversation-only:

\[
G=B(\mathcal{M})=(V_M\cup V_E, E_{EM}\cup E_{MM}).
\]

\(V_M\) contains Memory nodes, \(V_E\) contains normalized Entities,
\(E_{EM}\) contains Entity–Memory mention links, and \(E_{MM}\) contains
directed next/previous links between chronological neighbors. Questions enter
only through \(R_k(q;G)\).

The primary estimand is the paired difference in official evidence recall
between graph and matched dense retrieval. Final-answer F1 is a separate
downstream outcome; additional evidence is not automatically an answer-quality
improvement.

### 3.2 Conversation-only graph construction

For each conversation, the constructor consumes session timestamps, dialogue
ids, speaker names, dialogue text, and image captions. Each normalized
dialogue item becomes a Memory node. A requested `gpt-3.5-turbo` extractor at
temperature 0.3 identifies Entities. Entity strings are normalized,
case-insensitively deduplicated, and linked to Memories; deterministic speaker
links add the dialogue speaker as an Entity. Adjacent Memories receive
chronological edges.

The ten-conversation graph contains 5,882 Memory nodes. Graph construction
does not consume QA questions, gold answers, evidence annotations, category
labels, judge outputs, previous predictions, or question-driven ledgers.

**Figure 1 (rendered in the LaTeX paper).** (a) Ordinary dense RAG: a flat
Memory index with no Entity nodes and no chronological edges; the question
vector is ranked by cosine similarity and the top-\(k\) items go to the
reader, which may drop a neighboring Memory \(m_{t+1}\). (b) Conversation
turns first become an Entity–Memory graph; retrieval then gates, fuses,
recovers one-hop neighbors, and backfills, which can keep \(m_{t+1}\). Both
paths share Memory vectors, the query vector, top-\(k\), the requested
answer protocol, and the frozen evaluator. The neighbor annotation is
schematic. The control is the internal matched dense condition, not the
official LoCoMo DRAGON setup.

### 3.3 Entity-gated retrieval with chronological recovery

The question supplies normalized Entity keys \(Q_E(q)\) and a vector from a
complete artifact generated with OpenAI's
[`text-embedding-3-small`](https://developers.openai.com/api/docs/models/text-embedding-3-small)
model. The stored artifact is immutable and bound to dataset/question digests,
model, role, dimensions, normalization, and SHA-256. Formal retrieval fails on
a miss and makes no live query-embedding request.

Let \(\rho(e,u)\in[0,1]\) be peak-normalized Entity BM25. Exact normalized
equality receives one; matches below \(\tau=0.5\) are removed and at most 20
Entities are retained per key. The degree-discounted Entity score is:

\[
h(e,q)=\frac{1}{|Q_E^+(q)|}\sum_{u\in Q_E^+(q)}\rho(e,u)
       \frac{1}{\log(1+\deg(e))}.
\]

For Memory \(m\), \(c_m\) and \(w_m\) are the strongest incident content and
speaker Entity scores. A speaker-only match is dampened by \(\delta=0.25\):

\[
s_e^{(0)}(m,q)=
\begin{cases}
\max\{c_m,w_m\}, & c_m>0,\\
\delta w_m, & c_m=0.
\end{cases}
\]

One-hop sequence recovery is:

\[
s_e(m,q)=\max\left\{s_e^{(0)}(m,q),
\lambda\max_{m'\in N_{\mathrm{seq}}(m)}s_e^{(0)}(m',q)\right\}.
\]

In the experiments, \(\lambda\) is generally 0.5; sensitivity tests also use
0.25 and 1.0. The active candidate set contains Memories with positive Entity
score, with a full-pool fallback only when the set is empty. Entity and signed
cosine scores are fused as:

\[
s(m,q)=\alpha s_e(m,q)+\beta s_s(m,q).
\]

The primary setting uses \(\alpha=0.30\), \(\beta=0.70\). Candidates are
sorted by score and dialogue id. If the gate contains fewer than \(k\)
Memories, unused full-pool dense results fill remaining positions without
displacing gated items. The primary context budget (top-k) is 25; cutoff tests
use 5, 10, and 50.

## 4. Experimental Setup

### 4.1 Matched conditions and comparison boundary

The primary comparison holds constant dataset/order, Memory text and vectors,
immutable query vectors, requested answer prompt/model settings, evaluation,
output isolation, and aggregation. Treatment B activates Entity matching,
fusion, and chronological recovery. The dense graph-construction control
\(B_{embed}\) must reproduce A's ordered context ids for all rows.

The pinned DRAGON reproduction did not pass the declared tolerance and remains
diagnostic. Every metric-bearing condition uses an absent condition-specific
output and records source/configuration, artifact identities, query-cache
telemetry, prompt budget, and graph compliance. The vendored evaluator is
verified against its SHA-256 manifest.

### 4.2 Ablation study design

The matrix separates structural attribution, operating-condition stress tests,
local parameter sensitivity, and model substitution. Within each
family, only the listed treatment changes; the final row is diagnostic and is
not eligible for model-only inference.

| Family | Treatment and control | Fixed factors | Purpose |
|---|---|---|---|
| Structural components | Remove sequence recovery, Entity-score fusion, semantic scoring, or speaker links | Dataset, primary vectors, top-k 25, requested reader protocol, evaluator | Attribute the primary retrieval difference |
| Cutoff and input | Matched A/B at top-k 5, 10, 25, 50; raw versus time-annotated input | Paired rows and within-profile artifacts | Test context-budget and input dependence |
| Parameters | Entity/Semantic 0.10/0.90, 0.30/0.70, 0.50/0.50; sequence 0.25, 0.5, 1.0 | Complete-B graph and requested reader protocol | Bound local sensitivity |
| Robustness across configurations | Requested GPT-3.5 or DeepSeek extraction crossed with TES or Doubao embeddings | Complete B, top-k 25, requested extraction budget 2,500, requested GPT-3.5 reader protocol | Test extractor and embedding substitutions in a paper-eligible 2×2 matrix with outcome-specific robustness claims |
| Diagnostic only | Two GPT-5 mini extraction cells | Runtime extraction request was 4,000 rather than frozen 2,500 | Excluded from model-only inference pending rerun |

### 4.3 Evaluation protocol and statistical design

Retrieved Memory text/ids enter the frozen LoCoMo-aligned interface. The
requested answer alias is `gpt-3.5-turbo`, with system role, temperature 0,
batch one, and 32 completion tokens. The immutable package retains
category-specific generation/decoding, token F1, evidence recall, rounding,
and aggregation. Categories 1–4 subset F1 is a local diagnostic only.

Every condition covers 1,986 QA rows from ten conversations. Primary matched
contrasts use 10,000 paired-question and 10,000 conversation-cluster bootstrap
resamples, seed 20260727. Component/input/fusion/sequence families use Holm
correction within outcome and estimator.

The paper-eligible configuration matrix crosses two requested Entity
extractors with two embedding aliases and uses 10,000 whole-conversation
bootstrap resamples with seed 20260814. Holm correction is applied separately
to extraction/F1, extraction/recall, embedding/F1, and embedding/recall. The
preregistered sequential stop gate uses an absolute three-point band and is
triggered only when a 95% cluster interval lies wholly below −3 points or
wholly above +3 points. We report empirical robustness only as an
outcome-specific interpretation when a tested substitution has no
Holm-corrected rejection and does not trigger this gate; this is not a formal
equivalence test. Two completed GPT-5 mini cells are retained only as
diagnostic observations: their frozen records specify a 2,500-token extraction
limit, whereas the executed model-specific path used 4,000 tokens and 12 calls
exceeded 2,500. They are therefore excluded from the model-only robustness
claims and category ranges.

For all F1 contrasts, the requested GPT-3.5 alias, prompt, role, temperature,
and token budget are fixed, but the provider-returned deployment revision was
not recorded and Category-5 option order remains unseeded. We therefore treat
F1 as an observed downstream outcome under a matched requested protocol;
`recall_acc` provides the cleaner retrieval-stage comparison.

## 5. Results

### 5.1 Primary matched comparison

| Condition | Overall F1 | `recall_acc` |
|---|---:|---:|
| A (dense Memory) | 42.0681 | 79.7468 |
| \(B_{embed}\) (dense graph control) | 42.0677 | 79.7468 |
| B (complete graph retrieval) | **42.5680** | **84.4842** |

B improves `recall_acc` over A by 4.7374 percentage points. Paired-question
and conversation-cluster 95% intervals are 3.6504–5.8425 and
3.5286–6.0124 points; both two-sided p-values are 0.0002. F1 changes by
0.4998 points, with intervals −0.5745–1.5514 and −0.1773–1.2711; neither
supports a difference. A and \(B_{embed}\) have zero context mismatches over
all 1,986 rows and identical evidence recall.

### 5.2 Component analysis

| Contrast | ΔF1 | Δ`recall_acc` | Conclusion |
|---|---:|---:|---|
| B − B without sequence recovery | +0.5137 | +1.6728 | Recall supported; F1 not supported |
| B − B without Entity-score fusion | +0.8014 | +4.7626 | Recall supported; F1 not supported |
| Sequence recovery after Entity gating | −0.0609 | +0.4364 | Recall supported; F1 not supported |
| B − Entity-only retrieval | +5.0780 | +17.4634 | Both supported |
| Raw-text B − annotated-input B | +0.2407 | −0.2472 | Neither supported |
| Raw-text B − raw-text A | +0.3508 | +4.9522 | Recall supported; F1 not supported |
| B − B without speaker links | +0.2415 | +1.4822 | Recall supported; F1 not supported |

The opposite signs in the sequence-after-gating row are not contradictory.
For “How long have Mel and her husband been married?”, the gated control
misses D3:16 and produces an incorrect verbose sentence that nevertheless
receives F1 0.429. Sequence recovery retrieves D3:16 and answers the correct
“5 years”, raising recall 0→1 but receiving F1 0.364. Token overlap and
evidence coverage measure different stages.

### 5.3 Cutoff and input-profile robustness

| top-k | A F1 | B F1 | ΔF1 | A recall | B recall | Δrecall | Paired recall CI | Cluster recall CI |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 5 | 39.9053 | 39.8264 | −0.0790 | 59.3584 | 64.1667 | +4.8083 | [3.3450, 6.2808] | [2.8809, 6.6134] |
| 10 | 41.7607 | 42.1412 | +0.3805 | 68.9145 | 74.4847 | +5.5702 | [4.2928, 6.8624] | [4.2365, 6.7522] |
| 25 | 42.0681 | 42.5680 | +0.4998 | 79.7468 | 84.4842 | +4.7374 | [3.6504, 5.8425] | [3.5286, 6.0124] |
| 50 | 42.0782 | 41.7832 | −0.2950 | 86.7148 | 90.3306 | +3.6159 | [2.7754, 4.4735] | [2.4603, 4.6426] |

Recall intervals are above zero at every cutoff; corresponding F1 intervals
include zero. Time annotation has no supported within-B effect. Under raw
text, B retains a supported 4.9522-point recall advantage without an F1
advantage.

### 5.4 Parameter sensitivity

Changing Entity/Semantic weights from 0.30/0.70 to 0.10/0.90 lowers recall by
2.3062 points after correction; 0.50/0.50 is not distinguishable from the
primary setting. No F1 or recall contrast among sequence scales 0.25, 0.5,
and 1.0 survives family correction.

### 5.5 Outcome-specific robustness across requested configurations and descriptive category profile

TES denotes `text-embedding-3-small`, Doubao denotes
`doubao-embedding-vision`, and all table values are percentages.

| Requested extractor | Embedding alias | F1 | `recall_acc` |
|---|---|---:|---:|
| GPT-3.5 | TES | 42.5680 | 84.4842 |
| DeepSeek v4 Flash | TES | 42.1087 | 84.6005 |
| GPT-3.5 | Doubao | 42.1507 | 82.1978 |
| DeepSeek v4 Flash | Doubao | 42.8158 | 82.5778 |

Across the four protocol-matched cells, F1 spans 42.1087–42.8158. Neither the
two requested-extractor F1 contrasts nor their recall contrasts reject zero
after within-family Holm correction. These results support limited empirical
robustness of both outcomes across the tested GPT-3.5 and DeepSeek requested
extraction configurations, without establishing strict extractor equivalence.
The corresponding embedding F1 contrasts also do not reject zero, but the
Doubao frozen artifacts lower recall by 2.0227 points under DeepSeek
extraction and 2.2864 points
under GPT-3.5 extraction. Both recall contrasts remain supported after
correction. Each 95% cluster interval contains values on both sides of the
preregistered −3-point boundary, so neither interval triggers the gate for
material robustness failure. Passing that gate does not establish embedding
equivalence. Robustness across the tested embeddings is therefore
outcome-specific: F1 supports empirical robustness under the declared rule,
whereas evidence recall is sensitive to the frozen embedding artifacts.

Row-level examples show why the aggregate conclusion must remain
outcome-specific. With TES fixed, replacing GPT-3.5 extraction by DeepSeek on
“What gifts has Deborah received?” recovers one of five annotated turns
(recall 0 to 0.2), yet the independently generated answer changes from “A
bouquet from a friend” to “A bouquet” and token F1 falls from 0.44 to 0,
partly because the gold answer misspells *bouquet*. Conversely, with the
DeepSeek graph fixed, TES retrieves both annotated turns for the Voyageurs
National Park question (recall 1), whereas Doubao drops one (recall 0.5).
Doubao's incorrect “Unnamed national park” nevertheless receives F1 0.667,
above the TES answer's 0.138, because it shares a larger fraction of tokens
with the gold name. These cases do not establish single-row causal effects;
they document how stable aggregate F1 can coexist with observable retrieval
changes.

| Category | B F1 range | Dialog F1 | LightGMEM F1 | B recall range | Dialog recall | Descriptive position |
|---|---:|---:|---:|---:|---:|---|
| Multi-hop | 37.6–39.9 | 38.7 | 41.9 | 61.5–67.3 | 62.5 | B F1 range overlaps the Dialog anchor |
| Temporal | 40.2–43.1 | 37.2 | 56.4 | 89.2–90.2 | 83.5 | B recall is numerically above the Dialog anchor |
| Open-domain | 17.3–18.6 | 25.0 | 27.2 | 48.4–56.4 | 52.6 | Lowest B answer F1 range among Categories 1–4 |
| Single-hop | 63.8–64.1 | 59.9 | 64.1 | 91.1–92.7 | 87.1 | Highest B answer F1 range |
| Adversarial | 8.3–11.2 | 12.8 | — | 80.2–82.6 | 66.3 | B recall is numerically above Dialog; raw B F1 is lowest under the separate Category-5 branch |

The external rows are non-protocol descriptive anchors only. Original Dialog
uses historical DRAGON/reader infrastructure, LightGMEM uses GPT-4o-mini and
reports only Categories 1–4, and Mem0 headlines use an incommensurate
LLM-as-Judge metric. The table therefore does not establish cross-paper
superiority.

Concrete rows illustrate this profile. On the temporal question “Which classes
did Evan join in mid-August 2023?”, dense A misses D8:12 and answers “winter
activities” (recall 0, F1 0.2). B retrieves D8:12 together with its D8:13–14
neighbors and answers “Painting classes” (recall 1, F1 1.0). For the
single-hop question asking what keeps Evan busy while his knee heals, A
retrieves nearby D11 turns but omits D11:6 and answers “Swimming”; B adds
D11:6 at rank 19 and answers “Watercolor painting”, moving both outcomes from
0 to 1. These cases are consistent with Entity links locating the relevant
session and chronological recovery adding the exact adjacent fact; they do
not isolate either operation as the cause of a single-row outcome.

The weaker categories exhibit different retrieval and answer patterns. For
the open-domain Dr. Seuss question, both A and B retrieve the annotated
evidence that Caroline collects classic children's books, but their answers
omit the reference rationale and receive F1 0.222 and 0.118. In these stored
outputs, retrieving the annotated evidence is insufficient to match the
reference rationale. Conversely, for the adversarial question about what
inspired Melanie's art-show painting, B retrieves D9:16 whereas A does not,
yet both stored outputs receive F1 0 under the frozen Category-5 branch. This
row is consistent with the aggregate pattern of higher adversarial recall
without an answer-quality advantage; it does not identify the generation or
scoring branch as the cause.

### 5.6 Operational cost under cold and warm retrieval

| Provider stage | Cold requests | Input tokens | Output tokens | Cold summed call time | Warm requests |
|---|---:|---:|---:|---:|---:|
| Conversation Entity extraction | 5,873 | 3,731,393 | 425,637 | 9,792.76 s | 0 |
| Memory embedding | 591 | 214,229 | 0 | 443.38 s | 0 |
| Question Entity extraction | 1,974 | 1,214,259 | 104,272 | 2,970.83 s | 0 |

| Retrieval state (1,986 QA) | Provider requests | Mean/QA | p95/QA |
|---|---:|---:|---:|
| Cold | 0 | 1.5123 s | 2.6132 s |
| Warm | 0 | 0.004886 s | 0.006270 s |

The cold-to-warm retrieval speedup is 309.48×. Both states use the same 44
batches and immutable query artifact, with zero misses/live query embeddings;
warm includes a 1.29-second index load. Zero new pre-answer requests applies
only to replaying the same questions with complete caches. Including the
attached answer trace, the cold path uses 7,903,980 input and 546,178 output
tokens (8,450,158 total; 4,254.9/QA). The answer stage uses 1,389.9 tokens/QA.
The $4.67 illustrative conversion uses public prices accessed 1 August 2026
and excludes the separately built query artifact, storage/platform fees, and
unrecorded charges.

## 6. Discussion

The experiments separate evidence coverage from answer quality. Entity links,
semantic scoring, and chronological recovery retrieve more annotated evidence
than the matched dense control, and the difference persists across four
context budgets. Under the matched requested answer protocol, the
corresponding overall F1 difference is not supported. Reporting only answer
scores can therefore obscure retrieval changes, while retrieval gains should
not be described as end-to-end quality gains.

The semantic channel is the largest isolated contributor, with Entity fusion,
sequence recovery, and speaker links adding smaller supported recall gains.
Raw-text results show the B-over-A advantage does not depend on the tested time
annotation. Parameter results discourage presenting the primary settings as
universally optimal.

The configuration audit provides positive but bounded robustness evidence.
Across the four paper-eligible requested configurations, no
requested-extractor F1 or recall contrast rejects zero after Holm correction.
This supports limited empirical robustness across the tested GPT-3.5 and
DeepSeek requested extraction configurations, but it does not establish
extractor equivalence, independence from extraction, or arbitrary-model
invariance. The embedding result is mixed: F1 has no supported contrast,
whereas recall falls for the Doubao frozen artifacts relative to TES under the
fixed, uncalibrated 0.30/0.70 fusion. Robustness therefore applies to a
specified outcome and tested
configuration, not to unrestricted model exchange without retuning or
validation.

The category profile and cases are consistent with, but do not causally
identify, the intended retrieval mechanisms. In the audited single-hop and
temporal rows, Entity matching locates a relevant session and one-hop edges
add an adjacent turn. Open-domain rows can contain the annotated evidence
while their generated answers omit the reference rationale. Category 5 uses a
separate frozen option-generation and scoring branch, and the audited row
exhibits recall/F1 divergence under that branch. These observations place the
highest answer F1 in single-hop questions and higher recall than the original
Dialog@25 anchor in temporal and adversarial questions. They do not establish
a category-level causal effect or a protocol-matched cross-system advantage.

Cold/warm results expose an operational tradeoff. Conversation Entity
extraction and Memory embedding are one-time costs; uncached question-Entity
extraction dominates cold retrieval. Same-question replay is millisecond-scale
with complete caches, but unseen questions may require new calls.

**Limitations and future work.** Formal evidence covers ten conversations in
one LoCoMo release; cluster bootstrap does not establish cross-dataset
generalization. No matched cutoff supports an overall answer-F1 difference.
The official DRAGON reproduction gate did not pass. Actual provider deployment
revisions were not fully retained for reader, extraction, or embedding stages.
The matrix therefore supports outcome-specific empirical robustness across
the paper-eligible requested configurations represented by their frozen
artifacts, not robustness to fully identified provider deployments; a strict
deployment-level claim requires telemetry-complete reruns. Category 5 retains
upstream unseeded option order. The two GPT-5 mini cells have a frozen/runtime
extraction-budget mismatch (2,500 versus 4,000), with 12 calls exceeding
2,500, and remain diagnostic pending rebuild/rerun. A corrected
three-extractor robustness claim requires rebuilding and rerunning those cells
with one explicitly resolved budget; future graph-cache identities should
also bind extraction temperature and token budget. Timing comes from one
machine/provider, and the dollar conversion is not a frozen metric.

## 7. Conclusion

The conversation-only Entity–Memory graph improves official evidence recall
over matched dense retrieval on the evaluated LoCoMo set, while the overall
final-answer F1 difference is unsupported. Semantic scoring, Entity fusion,
chronological recovery, and speaker links account for the retrieval pattern.
The recall advantage persists across top-k 5–50 and raw text; parameter
sensitivity limits universal-optimum claims.

The paper-eligible requested-configuration matrix supports limited empirical
robustness of F1 and evidence recall across the tested GPT-3.5 and DeepSeek
extraction configurations. Embedding robustness is outcome-specific: neither
embedding F1 contrast rejects zero, whereas Doubao frozen artifacts reduce
recall by 2.02–2.29 points relative to TES. The corresponding intervals cross
the preregistered −3-point boundary, so the gate for material robustness
failure is not triggered, but embedding equivalence is not established.
Descriptive category ranges, supplemented by non-protocol external anchors,
place the highest answer F1 in single-hop questions, higher evidence recall
than Dialog@25 in temporal and adversarial questions, and the lowest answer F1
among Categories 1–4 in open-domain questions; adversarial raw F1 is lower
under its separate Category-5 branch. Cold/warm measurements also show that the graph and
retrieval artifacts can be reused for identical-question replay, although
unseen questions can require new provider calls. The ten-conversation sample,
two paper-eligible
requested extractors, two frozen embedding artifacts, failed official DRAGON
reproduction gate, single requested reader alias/protocol, and
single-environment latency measurement bound this scoped retrieval claim; the
results do not establish general answer-quality improvement, category-level
superiority, deployment-level robustness, or cross-dataset generalization.
Separating evidence coverage from answer quality provides a transferable
evaluation principle for future long-term conversational memory systems.

## Reproducibility and Responsible Use

**Reproducibility.** Formal conditions record source commit, resolved
configuration, dataset/artifact SHA-256 values, isolated output path,
query-cache use, token telemetry, graph-input audit, and prompt budget. Query
vectors are complete/read-only and the evaluator is vendored/hash-verified.

**Responsible use.** Conversation data can contain personal information.
Real deployments should establish consent, retention, deletion, and access
control. This work does not study privacy attacks or sensitive-memory
deletion.

## Data and Code Availability

LoCoMo data are available from the benchmark authors. Code, manifests,
validation records, and manuscript evidence snapshots are available at
<https://github.com/Sun668/em_graph_memory/tree/v1.0.8>.

## References

The authoritative bibliography is `arxiv/references.bib`. Key sources:

- Maharana et al. (2024), [Evaluating Very Long-Term Conversational Memory of LLM Agents](https://aclanthology.org/2024.acl-long.747/).
- Wu et al. (2025), [LongMemEval](https://arxiv.org/abs/2410.10813).
- Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.
- Karpukhin et al. (2020), Dense Passage Retrieval for Open-Domain Question Answering.
- Lin et al. (2023), [How to Train Your DRAGON](https://aclanthology.org/2023.findings-emnlp.423/).
- Gutiérrez et al. (2024), [HippoRAG](https://arxiv.org/abs/2405.14831).
- Edge et al. (2024), [GraphRAG](https://arxiv.org/abs/2404.16130).
- Chhikara et al. (2025), [Mem0](https://arxiv.org/abs/2504.19413).
- Anonymous (2026), [LightGMEM](https://openreview.net/forum?id=FCQR2oceJ1).
- OpenAI, [`text-embedding-3-small` model documentation](https://developers.openai.com/api/docs/models/text-embedding-3-small), accessed 16 August 2026.
