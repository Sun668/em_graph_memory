# Entity–Memory Bipartite Graphs for Long-Conversation Dialog Retrieval on LoCoMo

**Draft for arXiv (LoCoMo QA track only)**  
**Status:** matched-stack experiments complete (`gpt35_tes`, snapshot `v04_gpt35_tes_ab_ablation`)  
**Do not mix Mem0 / LLM-as-Judge scores into the main claims of this draft.**

---

## Abstract

Long multi-session conversations require retrieval that is both semantically flexible and entity-grounded. We study a conversation-only **Entity–Memory (EM)** bipartite graph for LoCoMo open-domain QA. Each dialog turn is a Memory node; LLM-extracted entities are Entity nodes linked by Mentions; consecutive turns are linked by dialog-order sequence edges. At query time we soft-match question entities to graph entities with BM25, expand ±1 neighbors along the dialog sequence, score the gated Memory pool with dense embeddings, and fuse the two signals as \(0.30\cdot E + 0.70\cdot S\).

To isolate the contribution of this retrieval structure, we rebuild the entire pipeline under a **matched stack**: entity extraction and answering with `gpt-3.5-turbo`, embeddings with `text-embedding-3-small`, and the LoCoMo short-answer protocol (token-F1 and evidence recall). On LoCoMo-10 (10 conversations, 1986 QA items), EM fusion retrieval (**System B**) reaches **46.48** token-F1@25 and **82.54%** recall_acc@25, improving over a plain full-corpus Dialog embedding RAG baseline (**System A**: 44.99 F1, 78.53% recall) by **+1.49** F1 points and **+4.01** recall points. Ablations show that entity-only ranking is insufficient (40.78 F1), embedding-only on the same Memory corpus nearly matches A (44.83 F1), and disabling sequence expansion yields a small drop (46.20 F1 / 80.77% recall). We cite LoCoMo paper Table-3 Dialog/Observation numbers only as external anchors, because the paper uses a different retriever (DRAGON).

---

## 1. Introduction

### 1.1 Problem

LoCoMo evaluates long-term conversational memory with multi-session dialogs and category-stratified QA (multi-hop, temporal, open-domain, single-hop, adversarial). The official RAG comparison in the LoCoMo paper reports **token-F1** of generated short answers and **retrieval recall** of gold evidence dialog IDs at several cutoffs \(k\). In that protocol, Dialog RAG, Observation RAG, and Summary RAG are alternatives that differ in the *unit of retrieval* (raw turns vs. speaker observations vs. session summaries).

Our work stays inside the **Dialog-family** setting: the system must retrieve dialog turns and answer from those turns. The research question is not whether to invent a new observation extractor for the main claim, but whether an **entity-aware graph over conversation turns** improves Dialog retrieval under a controlled stack.

### 1.2 Confounding risk and the matched-stack requirement

A high F1 number can be caused by a stronger embedder, a stronger reader LLM, a different prompt, or leakage of QA annotations into the memory store. Therefore the primary scientific comparison in this draft is:

> **System A vs System B under identical extraction model (when used), identical embedding model, identical answer model, identical answer prompt, identical dataset split, and identical metrics.**

Paper Table-3 numbers (Dialog F1@25 = 41.0, Dialog R@25 = 76.7, Observation best F1 = 43.3) are reported only as **external citations**. They use DRAGON retrieval in the original paper; we use `text-embedding-3-small`. Equality of reader (`gpt-3.5-turbo`) does **not** make the paper comparison a matched retriever comparison.

### 1.3 Contributions

1. A conversation-only Entity–Memory bipartite construction with Mentions and dialog-order Memory sequence edges, excluding QA fields from graph construction.
2. A retrieval procedure that combines BM25 entity soft-match gating, optional ±1 sequence expansion, and dense Memory scoring with fixed fusion weights \(0.30/0.70\).
3. A matched-stack LoCoMo-10 evaluation: plain Dialog dense RAG (A) vs EM fusion (B), plus entity-only / embed-only / no-sequence ablations, with full hyperparameters and logic specified below.

---

## 2. Related Work (brief)

**LoCoMo.** Maharana et al. introduce long multi-session conversations and evaluate long-context models and RAG variants (Dialog / Observation / Summary). Official QA metrics are token-level F1 and evidence recall; the paper’s RAG tables use DRAGON + GPT-3.5 for the reported Dialog/Observation/Summary numbers we cite.

**Graph / entity memory.** Memory graphs and entity-centric indexes are common in conversational agents. Our design is deliberately narrow: bipartite Entity–Memory over **conversation turns only**, with retrieval that returns dialog IDs for a LoCoMo-style short reader. We do not claim industrial LLM-judge protocols (e.g. Mem0-style J-scores) in the main tables.

---

## 3. Method

### 3.1 Data objects (conversation only)

For each LoCoMo sample \(c\) with sample ID (e.g. `conv-26`), the conversation object contains sessions `session_i`, each a list of dialogs with fields used at graph build time:

| Field | Used in graph? | Role |
|---|---|---|
| `dia_id` | yes | Memory identity; retrieval returns these IDs |
| `speaker` | yes | Memory attribute; pronoun replacement; embedding text |
| `text` | yes | Raw utterance; stored on Memory |
| `blip_caption` / `img_caption` | yes | Optional image caption attached to Memory |
| `session_*_date_time` | yes | Session timestamp on each Memory; used in answer context and temporal QA suffix |
| QA `question` / `answer` / `evidence` / `category` | **no** | Forbidden at graph construction; used only at evaluation / query time |

**Hard constraint.** Graph construction must not consume QA questions, gold answers, gold evidence annotations, category labels, judge outputs, or previous predictions. Question-side entity extraction happens at **query time** and does not write into the stored graph.

### 3.2 Preprocessing: `replace_pronouns`

Before entity extraction, each dialog text is normalized with `replace_pronouns(text, speaker, previous_speaker, dialog_time)`:

- First-person pronouns (`I`, `me`, `my`, …) → current speaker name.
- Second-person pronouns → previous speaker name when available.
- Relative time words can be resolved against `dialog_time` (session date string).

The Memory node stores both `text` (raw) and `text_normalized` (after replacement). Entity extraction runs on the normalized dialog string (plus caption text when present in the builder’s extraction text helper).

### 3.3 Graph schema

**Node types**

1. **Memory** \(m\): one per dialog turn.  
   Attributes: `id = memory:{dia_id}`, `dia_id`, `session_num`, `date_time`, `speaker`, `text`, `text_normalized`, `blip_caption`, optional `query`/`img_url` as stored by the dataset.

2. **Entity** \(e\): LLM-extracted concept with type in  
   \(\{\texttt{Who},\texttt{What},\texttt{When},\texttt{Where},\texttt{Why},\texttt{How},\texttt{How much}\}\).  
   Canonicalized by `normalize_entity_key(value)`.

**Edge types**

1. **Mentions** (Entity ↔ Memory): created when an entity is extracted from that dialog’s extraction text. Edge weight defaults to 1.0 unless otherwise set by the builder.
2. **Sequence** (Memory ↔ Memory): for consecutive dialogs in conversation order, add bidirectional `NEXT` and `PREV` edges (`ensure_memory_sequence_edges`).

The graph is asserted bipartite between Entity and Memory for Mentions; sequence edges are Memory–Memory and are stored separately as `memory_edges`.

### 3.4 Entity extraction (build time and query time)

**Version.** `ENTITY_EXTRACT_VERSION = "v4"`.

**Model (this paper’s matched stack).** `gpt-3.5-turbo` via `OPENAI_MODEL`.

**Prompt (scaffold length 2430 characters).** The extractor uses a fixed instruction that:

1. Restricts types to the set above.
2. Prefers short noun phrases (about 1–3 words).
3. Encourages subject–predicate–object coverage when present (subject as Who, predicate as What, object typed by meaning).
4. Forbids interrogatives, function words, auxiliaries/copulas/generic verbs without retrieval value.
5. Requests a JSON array of `{"value","type"}` only.

Temperature for extraction chat calls is **0.3**; token budget **2500** for non-`gpt-5` models; up to 3 parse retries.

**Speaker entity.** Config flag `add_speaker_as_entity=True` (package default) also attaches the speaker as a Who-like entity where implemented by the builder.

**Query-time keys.** For each evaluation question, the same extractor produces a set of entity keys \(Q\). These keys are cached per sample under  
`outputs/em_graph/{sample}_qkeys_gpt35_tes.json`  
and are **not** written into the conversation graph.

### 3.5 Dense Memory index

For each Memory \(m\), the embedding string is:

```text
memory_search_text(m) = join(text_normalized, text, speaker, blip_caption, query)
```

**Embedding model (matched stack):** `text-embedding-3-small` (`EM_GRAPH_EMBED_MODEL`).

**Index:** cosine similarity of L2-usable vectors as implemented in `MemoryEmbeddingIndex.scores` (dot product after the package’s embedding normalization path; non-positive sims clipped at 0 in the score dict).

**Cache policy in the publish runner:** shared cross-model text caches are **disabled** (`use_text_cache=False`) to avoid mixing vectors from a previous embedder dimension (e.g. 2048 vs 1536). Per-sample `.npz` caches are used:

- EM graphs: `{sample}_memory_emb_extract_v4_gpt35_tes_text-embedding-3-small.npz`
- System A memory-only graphs: `{sample}_memory_emb_memory_only_gpt35_tes_text-embedding-3-small.npz`

### 3.6 Entity BM25 soft-match

Build `EntityBM25Index` over all Entity nodes. Each entity document is `key` and/or `value` tokenized by `tokenize_for_bm25`.

For each question key \(q_k \in Q\):

1. Score all entities with BM25Okapi; **peak-normalize** scores for that key to \([0,1]\).
2. Exact normalized key equality forces score \(1.0\).
3. Keep entities with score \(\ge 0.5\) (`min_rel_score=0.5`), at most **20** entities per question key (`top_k_per_key=20`).

Output: map \(\texttt{entity_id} \mapsto \{q_k: \mathrm{match\_score}\}\).

### 3.7 Entity → Memory seed scores

Let \(\mathcal{E}(q)\) be matched entities. Define per-entity raw strength:

\[
\mathrm{raw}(e)=\left(\frac{\sum_{q_k}\mathrm{match}(e,q_k)}{|Q_{\mathrm{eff}}|}\right)\cdot\frac{1}{\log(1+\deg(e))}
\]

where \(Q_{\mathrm{eff}}\) is the set of question keys that matched at least one entity, and \(\deg(e)\) is the number of Mentions edges of \(e\).

Propagate to Memory nodes via Mentions. Who-like matches (entity type Who, or matches only against Who-linked question keys) and content matches are tracked separately. If a Memory has any content score \(c>0\), its entity score is \(\max(c,w)\); if only Who scores exist, dampen by \(0.25\):

\[
E_{\mathrm{seed}}(m)=\begin{cases}
\max(c,w) & c>0\\
0.25\cdot w & c=0,\ w>0\\
0 & \text{otherwise.}
\end{cases}
\]

### 3.8 Sequence expansion

If enabled, for each seed Memory with score \(s>0\), add each dialog-order neighbor \(n\) (via NEXT/PREV adjacency) with

\[
E(n)\leftarrow\max\bigl(E(n),\ 0.5\cdot s\bigr).
\]

Seeds keep their original scores. Expansion is **one hop**.

### 3.9 Fusion ranking (System B default)

Let \(E(m)\) be the (possibly expanded) entity score and \(S(m)\) the dense score of Memory \(m\) against the question embedding.

**Gating.** If the entity score map is non-empty, the candidate pool \(\mathcal{P}\) is the support of \(E\); dense scores are computed **only on** \(\mathcal{P}\). If the entity map is empty (no usable question keys or no matches), fall back to the **full** Memory corpus.

**Fusion.**

\[
\mathrm{score}(m)=0.30\cdot E(m)+0.70\cdot S(m)
\]

Sort by score descending (tie-break by `dia_id`), return top-\(k\) dialog IDs.

**Constants used in code:**  
`entity_weight=0.30`, `semantic_weight=0.70`, `_SEQUENCE_SECONDARY_SCALE=0.5`, `_WHO_ONLY_DAMPEN=0.25`.

### 3.10 Answer generation (shared by all systems)

Retrieved dialog IDs are mapped back to Memory nodes. Context lines are:

```text
{date_time}: {speaker} said, "{text}"[ and shared {blip_caption}]
```

joined by newlines, in retrieval order, truncated to **top-25** for answering.

**Reader model:** `gpt-3.5-turbo`.  
**Decoding:** `temperature=0`, default `max_tokens=512` with up to 4 attempts doubling to at most 2048 on empty/failure.  
**Wait:** `EM_GRAPH_WAIT_TIME` default 0.15s in the runner; workers `EM_GRAPH_MAX_WORKERS=8`.

**Prompts.**

- Default (categories ≠ 5):

```text
Based on the above context, write an answer in the form of a short phrase for the following question. Answer with exact words from the context whenever possible.

Question: {question} Short answer:
```

- Temporal (category = 2): append  
  ` Use DATE of CONVERSATION to answer with an approximate date.`  
  to the question before the template.

- Adversarial (category = 5):

```text
Based on the above context, answer the following question. If the answer is not mentioned in the conversation, reply exactly: Not mentioned in the conversation.

Question: {question} Short answer:
```

The full model input is `context + "\n\n" + template`.

### 3.11 Metrics

**Token-F1.** Lowercase alphanumeric tokenization (`[a-z0-9]+`). Let \(G,P\) be gold/pred token sets. If both empty → 1; if either empty → 0; else

\[
\mathrm{F1}=\frac{2pr}{p+r},\quad p=\frac{|G\cap P|}{|P|},\ r=\frac{|G\cap P|}{|G|}.
\]

Reported as mean ×100 over QA items at the answer cutoff \(k=25\). We also report **ex-cat5** means (exclude adversarial category 5) as a diagnostic, not as the primary overall number.

**recall_acc@\(k\).** For gold evidence dialog ID list \(E\) (from the dataset; evaluation-only) and retrieved list \(R_k\),

\[
\mathrm{recall\_acc}=\frac{|\{e\in E:e\in R_k\}|}{|E|}
\]

(empty \(E\) → 1.0 by implementation). We also report binary **hit@\(k\)**: 1 iff \(E\cap R_k\neq\emptyset\) (empty \(E\) → hit).

**Category map in data:** 1 Multi-hop, 2 Temporal, 3 Open-domain, 4 Single-hop, 5 Adversarial. Overall includes category 5 unless labeled ex-cat5.

---

## 4. Experimental Setup

### 4.1 Dataset

- File: `data/locomo10.json`
- Conversations: 10 (`conv-26,30,41,42,43,44,47,48,49,50`)
- QA items evaluated: **1986** (all items with non-empty questions in the runner)

### 4.2 Environment (matched stack)

```bash
source env_gpt.sh
# OPENAI_MODEL=gpt-3.5-turbo
# MODEL=gpt-3.5-turbo
# EM_GRAPH_EMBED_MODEL=text-embedding-3-small
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
```

Artifact tag: `gpt35_tes`.  
Runner: `experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py`.  
Package: `em_graph/` (Entity–Memory; no cross-imports with `graph_memory/`).

### 4.3 Graph statistics (gpt-3.5 extract-v4)

Built with `run_publish_stack.py build-graphs` (ProcessPool, default 2 graph workers; extract workers from `EM_GRAPH_EXTRACT_WORKERS` default 6). Checkpoint every 40 dialogs.

| Sample | Memories | Entities | Mentions edges | Sequence edges (NEXT+PREV count in stats) |
|---|---:|---:|---:|---:|
| conv-26 | 419 | 1120 | 2765 | 836 |
| conv-30 | 369 | 784 | 2151 | 736 |
| conv-41 | 663 | 1487 | 4204 | 1324 |
| conv-42 | 629 | 1255 | 3335 | 1256 |
| conv-43 | 680 | 1534 | 4038 | 1358 |
| conv-44 | 675 | 1281 | 3786 | 1348 |
| conv-47 | 689 | 1521 | 3944 | 1376 |
| conv-48 | 681 | 1446 | 3786 | 1360 |
| conv-49 | 509 | 1079 | 2750 | 1016 |
| conv-50 | 568 | 1241 | 3643 | 1134 |

Paths: `outputs/em_graph/{sample}_em_graph_extract_v4_gpt35_tes.json`.

### 4.4 Systems and exact retrieval knobs

All systems answer with the same reader/prompt at **top-25**. Retrieval also materializes top-50 for multi-\(k\) recall sheets.

| ID | Graph | \(w_E\) | \(w_S\) | Sequence expand | Entity keys at query | Candidate pool |
|---|---|---:|---:|---|---|---|
| **A** | Memory-only (no LLM entity extract) | 0.0 | 1.0 | off | none (`force_full_pool`) | all Memories |
| **B** | EM extract-v4 | 0.30 | 0.70 | on (±1 @ 0.5) | LLM q-keys | entity-gated; full if empty |
| **B_entity** | EM extract-v4 | 1.0 | 0.0 | on | LLM q-keys | entity-gated; full if empty |
| **B_embed** | EM extract-v4 | 0.0 | 1.0 | off | forced empty set | all Memories |
| **B_noseq** | EM extract-v4 | 0.30 | 0.70 | off | LLM q-keys | entity-gated; full if empty |

**System A construction detail.** A does not wait for EM entity extraction. It builds a Memory-only graph from the same conversation fields (pronoun normalization, captions, sequence edges for schema completeness) but never uses Mentions for retrieval because \(w_E=0\) and `force_full_pool` clears q-keys. This allows A to run in parallel with EM graph building.

**System B_embed detail.** Memories come from the EM graph (entities exist on disk but are unused). Query entity keys are forcibly set to \(\emptyset\), so retrieval is full-corpus cosine ranking—the intended “dense-only control on the same Memory units as B.”

### 4.5 Commands

```bash
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py build-graphs
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py A
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py B
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py ablation
python experiments/exp_2026_07_26_locomo_official_compare/run_publish_stack.py summarize
```

Result JSONs: `result_gpt35_tes_{label}.json`.  
Compare table: `TABLE_GPT35_TES_COMPARE.md`.  
Immutable snapshot: `snapshots/v04_gpt35_tes_ab_ablation/`.

### 4.6 What is *not* in the main experiment

- Mem0 J-score / LLM-as-Judge promotion metrics.
- Self-built Observation or Summary memories as a main system (an earlier oracle probe on dataset fields under TES + gpt-3.5 scored Obs@25 F1 32.69 and Summary@10 F1 30.21, far below Dialog-family results; we do not promote Obs/Summary self-build here).
- Doubao-embedding graphs or the earlier frozen-evidence F1 46.18 run as this stack’s headline (different embedder / graph lineage).

---

## 5. Results

### 5.1 Main matched-stack comparison (overall)

| System | token-F1@25 | ex-cat5 F1@25 | recall_acc@25 | hit@25 | recall_acc@5 | @10 | @50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A plain Dialog embed | 44.99 | 50.20 | 78.53 | 83.69 | 56.95 | 67.21 | 85.61 |
| **B EM 0.3/0.7 + seq** | **46.48** | **51.68** | **82.54** | **87.56** | **62.82** | **72.92** | **88.82** |
| B_entity | 40.78 | 45.27 | 65.99 | 71.75 | 41.98 | 52.37 | 73.41 |
| B_embed | 44.83 | 49.99 | 78.53 | 83.69 | 56.95 | 67.26 | 85.56 |
| B_noseq | 46.20 | 51.05 | 80.77 | 85.95 | 60.70 | 70.62 | 86.72 |

**Deltas (B − A):** F1 **+1.49** absolute points; recall_acc@25 **+4.01** points; hit@25 **+3.87** points.

**Promotion gate used in the repository.**  
If \( \mathrm{F1}(B)>\mathrm{F1}(A) \) and \( \mathrm{recall@25}(B)\ge\mathrm{recall@25}(A) \), label `publish_ok_method_helps`. This run satisfies the gate.

### 5.2 Category breakdown at \(k=25\) (F1 and recall_acc)

**System A**

| Category | n | F1@25 | recall_acc@25 | hit@25 |
|---|---:|---:|---:|---:|
| Multi-hop | 282 | 38.73 | 60.96 | 86.52 |
| Temporal | 321 | 42.55 | 88.89 | 91.28 |
| Open-domain | 96 | 17.60 | 50.91 | 62.50 |
| Single-hop | 841 | 60.69 | 87.22 | 88.11 |
| Adversarial | 446 | 26.98 | 71.75 | 72.65 |

**System B**

| Category | n | F1@25 | recall_acc@25 | hit@25 |
|---|---:|---:|---:|---:|
| Multi-hop | 282 | 38.88 | 59.97 | 84.40 |
| Temporal | 321 | 42.17 | 90.19 | 92.52 |
| Open-domain | 96 | 20.05 | 56.42 | 68.75 |
| Single-hop | 841 | 63.22 | 90.61 | 91.44 |
| Adversarial | 446 | 28.53 | 81.73 | 82.74 |

**Reading the category table (not a slogan).**  
Overall gains are driven especially by Single-hop (F1 60.69→63.22; recall 87.22→90.61) and Adversarial recall (71.75→81.73) / F1 (26.98→28.53), with Open-domain also improving (F1 17.60→20.05; recall 50.91→56.42). Multi-hop F1 is nearly flat (38.73→38.88) while Multi-hop recall_acc slightly decreases (60.96→59.97); hit@25 also dips (86.52→84.40). Temporal F1 is slightly lower (42.55→42.17) while temporal recall rises (88.89→90.19). These mixed per-category movements are why we require the **joint** overall F1 and overall recall gate rather than claiming uniform gains on every category.

### 5.3 Ablation: what each component does

#### 5.3.1 Entity-only (`B_entity`: \(w_E=1,w_S=0\), sequence on)

Full-corpus semantics are removed; ranking uses only entity-propagated scores (with sequence expansion). Overall F1 falls to **40.78** and recall_acc@25 to **65.99%**, below both A and B.  
Interpretation with mechanism: entity soft-match can surface Mentions-linked turns, but without dense scoring the ranker cannot break ties among many entity-related Memories using question paraphrase similarity. Entity gating is a **candidate generator / feature**, not a complete ranker.

#### 5.3.2 Embed-only full pool (`B_embed`: \(w_E=0,w_S=1\), no sequence, forced empty q-keys)

This forces `retrieve_dialog_ids` into the ungated branch: cosine against **all** Memory nodes on the EM graph. Results: F1 **44.83**, recall_acc@25 **78.53%**, essentially matching A (44.99 / 78.53). Small F1 differences are consistent with (i) Memory text coming from the EM graph object vs A’s memory-only graph object and (ii) answer-sample variance under the same decoding settings—not with entity fusion.  
Interpretation: simply storing entities on disk does nothing if they are not used in scoring; the matched gain of B over A is not explained by “using the EM file format.”

#### 5.3.3 No sequence (`B_noseq`: \(0.3/0.7\), sequence off)

Removing ±1 expansion yields F1 **46.20** and recall_acc@25 **80.77%**. Relative to B: **−0.28** F1, **−1.77** recall points.  
Interpretation: neighbors of entity-seeded turns help evidence coverage moderately (especially when gold evidence is adjacent to an entity-matched turn), but the dominant lift vs A already appears from entity-gated fusion without sequence.

#### 5.3.4 Causal summary of the ablation design

```
If gain were only “different Memory text packaging”
  → B_embed should beat A substantially
  → observed: B_embed ≈ A  ⇒ rejected

If gain were only “entities without semantics”
  → B_entity should approach B
  → observed: B_entity ≪ B  ⇒ rejected

If gain were mostly sequence edges
  → B_noseq should collapse toward A
  → observed: B_noseq still ≫ A on both metrics; gap to B is small
  ⇒ sequence is helpful but secondary

Remaining explanation consistent with data:
  entity soft-match defines a question-conditioned Memory pool,
  dense scores rank inside (or fall back to full corpus),
  fusion 0.3/0.7 combines both.
```

### 5.4 External citation: LoCoMo paper Table 3

| Source | Setting | F1 | Recall@25 |
|---|---|---:|---:|
| Paper Dialog RAG | DRAGON + gpt-3.5, @25 | 41.0 | 76.7 |
| Paper Observation (best F1 in paper) | DRAGON + gpt-3.5 | 43.3 | (paper table) |
| Paper Summary | DRAGON + gpt-3.5, @10 F1 | 32.0 | — |
| **Our B (this work)** | TES + gpt-3.5, @25 | **46.48** | **82.54** |
| **Our A (this work)** | TES + gpt-3.5, @25 | 44.99 | 78.53 |

We **do not** treat (B − paper Dialog) as a controlled ablation of “Entity–Memory vs DRAGON,” because the dense encoders differ. The controlled claim is **B vs A**.

---

## 6. Implementation Notes Affecting Fairness

1. **Empty question-entity path.** If \(Q=\emptyset\), BM25 matching is skipped (no division-by-zero on empty effective key sets); retrieval becomes full-corpus dense ranking even for B.
2. **Who-only dampening (0.25).** Prevents person-name-only matches from dominating when no content entity links to the Memory.
3. **Degree weighting** \(1/\log(1+\deg(e))\) downweights ubiquitous entities.
4. **Answer context order** follows retrieval rank, not chronological order.
5. **Prompt budget.** Extraction scaffold is 2430 characters; answer templates are short LoCoMo-style phrases. Non-data scaffolds remain under a 5000-character project limit.

---

## 7. Limitations

1. **Retriever mismatch vs paper.** DRAGON ≠ `text-embedding-3-small`. Paper rows are citations.
2. **Extract model quality.** Entities are produced by `gpt-3.5-turbo` v4 prompts; stronger extractors might change absolute numbers (a separate study).
3. **Multi-hop category.** Overall gains do not imply Multi-hop recall improvement; multi-hop remains an open error-analysis target.
4. **No long-context no-retrieval ceiling** in this draft (LoCoMo Table-2 style).
5. **No second benchmark** (e.g. LongMemEval) in this draft.
6. **English LoCoMo only**; pronoun/time normalization heuristics are English-oriented.
7. **Industrial judge metrics** are out of scope for the main table by design.

---

## 8. Reproducibility Checklist

- [ ] `source env_gpt.sh` with `gpt-3.5-turbo` + `text-embedding-3-small`
- [ ] `ENTITY_EXTRACT_VERSION == "v4"`
- [ ] Build graphs with tag `gpt35_tes` (or reuse committed graph stats + local `outputs/`)
- [ ] Run A, B, ablation, summarize via `run_publish_stack.py`
- [ ] Confirm gate from `TABLE_GPT35_TES_COMPARE.md`
- [ ] Snapshot sources under `snapshots/v04_gpt35_tes_ab_ablation/`
- [ ] Verify graph audit: conversation-only inputs; QA excluded from construction
- [ ] Do not report Mem0 J-score in the main LoCoMo table

Exact result files for this draft:

- `result_gpt35_tes_plain_dialog_embed.json` (A)
- `result_gpt35_tes_em_full_0.3_0.7.json` (B)
- `result_gpt35_tes_em_entity_only.json`
- `result_gpt35_tes_em_embed_fullpool.json`
- `result_gpt35_tes_em_full_noseq.json`
- `result_gpt35_tes_compare_summary.json`
- `result_build_graphs_gpt35_tes.json`

---

## 9. Conclusion

Under a single fixed stack—`gpt-3.5-turbo` extract-v4, `text-embedding-3-small` Memory embeddings, and `gpt-3.5-turbo` LoCoMo short answering—Entity–Memory fusion retrieval with weights \(0.30/0.70\) and ±1 sequence expansion improves both token-F1@25 and evidence recall_acc@25 over plain Dialog embedding RAG on LoCoMo-10. Ablations locate the gain in the **combination of entity-conditioned candidate formation and dense ranking**, not in entity scores alone, not in the mere presence of an EM graph file, and only partly in sequence edges. This is the claim suitable for the main arXiv narrative; comparisons to LoCoMo paper Table 3 must keep the DRAGON-vs-TES caveat explicit.

---

## Appendix A — Retrieval pseudocode (System B)

```
Input: graph G, question q, top_k
Q ← ExtractEntityKeys(q)   # gpt-3.5-turbo, extract-v4 prompt
if Q non-empty:
    M ← BM25SoftMatchEntities(G, Q; min_rel=0.5, top_k_per_key=20)
    E_seed ← PropagateMentionsWithWhoDampening(G, M)
    if expand_sequence:
        E ← ExpandDialogNeighbors(E_seed, scale=0.5)
    else:
        E ← E_seed
else:
    E ← {}

if E non-empty:
    pool ← keys(E)
    S ← EmbedScores(q, pool)
else:
    pool ← all Memory ids
    S ← EmbedScores(q, pool)

for m in pool:
    score[m] ← 0.30 * E.get(m,0) + 0.70 * S.get(m,0)
return top_k dia_ids by score
```

## Appendix B — System A / B_embed ungated branch

```
Q ← ∅                 # forced for A/B_embed via force_full_pool
E ← {}
pool ← all Memory ids
S ← EmbedScores(q, pool)
score[m] ← 1.0 * S[m]
return top_k dia_ids
```

## Appendix C — Category ID mapping

| ID | Name |
|---|---|
| 1 | Multi-hop |
| 2 | Temporal |
| 3 | Open-domain |
| 4 | Single-hop |
| 5 | Adversarial |

---

## Appendix D — One-sentence claims allowed / disallowed

**Allowed.**  
“Under gpt-3.5-turbo + text-embedding-3-small, Entity–Memory 0.3/0.7 fusion with sequence expansion improves LoCoMo-10 Dialog RAG token-F1@25 from 44.99 to 46.48 and recall_acc@25 from 78.53% to 82.54% versus plain Dialog embedding RAG.”

**Disallowed without caveat.**  
“We beat LoCoMo paper Observation RAG by X points” as a matched claim (retriever differs).  
“Our method reaches 46.18 F1” referring to the doubao-embedding lineage as if it were this stack.  
“Mem0 J-score 83% proves LoCoMo Table-3 superiority.”
