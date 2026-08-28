# Journal-neutral manuscript materials

Journal word limits, citation style, and submission requirements have not been
specified. This file supplies evidence-bound Results, Discussion, and
Limitations text. Literature positioning and a final Abstract should be added
only after the target venue and citation set are fixed.

## Working title

Entity–Memory Graph Retrieval Improves Evidence Coverage in Long-Conversation
Question Answering

## One-sentence contribution

A conversation-built Entity–Memory graph improves retrieval of annotated
evidence over a matched dense Memory control across four retrieval cutoffs,
while the same experiments do not establish higher overall answer F1.

## Research questions

1. Does Entity–Memory graph retrieval improve evidence recall over matched
   dense Memory retrieval when query vectors, Memory vectors, answer
   generation, and evaluation are held fixed?
2. Which graph and retrieval components contribute to the observed difference?
3. Does the result persist across retrieval cutoffs and selected input,
   fusion-weight, and sequence-scale settings?

## Methods synopsis

The evaluation used ten LoCoMo conversations containing 1,986 question–answer
rows. Graph construction consumed session timestamps, dialog identifiers,
speakers, dialog text, and image captions. It excluded questions, answers,
evidence annotations, category labels, predictions, and evaluator output.
Each dialog item formed a Memory node. Extracted and normalized entities formed
Entity nodes connected to the Memory nodes in which they occurred, and
chronological edges linked adjacent Memory nodes.

The primary graph condition combined Entity matching and semantic Memory
similarity with weights 0.30 and 0.70. It used an Entity threshold of 0.5,
retained up to 20 Entity matches per query key, dampened speaker-only matches
by 0.25, applied degree discounting, and expanded chronological neighbors at
scale 0.5. The matched control ranked the same Memory representations by
semantic similarity alone. All matched comparisons used the same ordered
read-only query vectors, and formal retrieval made no live query-embedding
requests.

The frozen evaluator generated one answer per question with the requested
`gpt-3.5-turbo` model, temperature 0, and a 32-token completion limit.
Official per-row F1 and evidence recall were aggregated over all 1,986 rows.
Uncertainty was estimated with 10,000 paired-QA bootstrap resamples and 10,000
resamples of whole conversations. Component, input, fusion, and sequence
families used Holm step-down correction within each outcome and estimator.

## Results

### Primary matched comparison

Entity–Memory retrieval improved evidence recall at the primary cutoff without
an established overall answer-F1 gain. At top-k 25, the dense Memory control
reached 79.7468% `recall_acc`, whereas the complete graph condition reached
84.4842%. The 4.7374-point difference had a paired-QA 95% interval of
3.6504–5.8425 points and a conversation-cluster interval of 3.5286–6.0124
points. Overall F1 was 42.0681% for the control and 42.5680% for the graph
condition. The corresponding 0.4998-point difference was not supported by
either bootstrap estimator.

The dense graph-construction control showed that graph construction alone
did not alter dense retrieval. B_embed and the Memory-only control returned the
same ordered context identifiers for every QA row and had identical
`recall_acc` of 79.7468%. Their overall F1 values differed by less than 0.001
percentage points, consistent with the frozen evaluator’s unseeded Category-5
option ordering rather than a retrieval difference.

### Cutoff analysis

The evidence-recall advantage persisted across all preregistered cutoffs. The
B−A differences were 4.8083 points at top-k 5, 5.5702 points at top-k 10,
4.7374 points at top-k 25, and 3.6159 points at top-k 50. Paired-QA and
conversation-cluster intervals were above zero at every cutoff. In contrast,
the matched overall F1 interval included zero at each cutoff. The cutoff
analysis therefore supports a retrieval-coverage result over top-k 5–50, not a
general improvement in generated answers.

### Component and input analyses

The component analyses locate the retrieval gain in several parts of the graph
path. Sequence expansion, Entity-score fusion, and sequence expansion after
Entity gating each improved `recall_acc` after Holm correction, although none
of these contrasts improved overall F1. Adding the semantic channel to
Entity-only retrieval improved both outcomes within the component family.
Removing deterministic speaker links reduced `recall_acc` by 1.4822 points
without a supported F1 change.

Input and parameter analyses narrow the scope of these component findings.
Removing time annotations produced no corrected overall difference within B,
while B retained a 4.9522-point recall advantage over A when both used raw
text. A fusion setting that reduced the Entity weight from 0.30 to 0.10 lowered
recall by 2.3062 points. Equal 0.50/0.50 weights did not differ from the primary
setting. No overall F1 or recall contrast among sequence scales 0.25, 0.5, and
1.0 survived family correction.

### System cost

The complete primary graph condition was measured under an isolated cold cache
and an immediate warm replay over all 1,986 questions. Cold construction made
5,873 conversation-Entity requests and 591 Memory-embedding requests. Cold
question processing made 1,974 question-Entity requests. Replaying the same
question set with complete graph, index, query-vector, and question-Entity
caches made zero new requests in all three stages. Mean retrieval latency
decreased from 1.5123 seconds per question when question Entities were uncached
to 0.004886 seconds in the warm replay; this is a 309.48× cold-to-warm speedup.
The corresponding p95 values were 2.6132 and 0.006270 seconds. Unseen questions
may still require query embedding and question-Entity calls.

The stored graph, Memory-index, and Entity/question-cache artifacts occupied
21.69 MB, 29.95 MB, and 3.41 MB, respectively. Including the validated answer
trace, the cold path used 7,903,980 input and 546,178 output tokens, or
8,450,158 total tokens. This corresponds to 4,254.9 tokens per question; the
answer stage accounts for 1,389.9 tokens per question. These stage timings
overlap and are not an end-to-end latency sum. At OpenAI public list prices
accessed on 1 August 2026, the measured usage gives an illustrative $4.67 total
or $0.00235 per question. The conversion is not a frozen metric and excludes
the separately built query-vector artifact, storage, platform fees, and
unrecorded external charges.

## Discussion

The experiments separate retrieval coverage from final answer quality. Entity
links, semantic ranking, and chronological expansion retrieved more annotated
evidence than dense Memory ranking alone, and the difference remained present
across four cutoffs. The frozen answer generator did not convert this additional
coverage into a statistically supported overall F1 gain. Retrieval and
generation should therefore be treated as distinct stages when evaluating
long-conversation memory systems.

The ablations suggest that no single graph operation accounts for the complete
recall difference. Semantic scoring supplied the largest isolated contribution,
while Entity fusion, sequence expansion, and speaker links made smaller
contributions to evidence coverage. The raw-text comparison indicates that the
B-over-A recall result does not depend on the tested time annotations. These
findings support the graph retrieval mechanism within this experiment design,
but they do not establish that every component will transfer unchanged to
another dataset or answer model.

The answer-level null result also constrains method claims. More retrieved
evidence can be redundant, weakly ordered, or difficult for a short answer
decoder to use. The present experiments do not distinguish among these
possibilities, and a new answerer would change the generation protocol.
Future work should test evidence selection and answer generation as separately
preregistered factors rather than describing recall gains as answer-quality
gains.

## Limitations and future work

First, the formal evidence comes from one ten-conversation LoCoMo set. This
limits claims to the evaluated sample. Replication on additional
long-conversation datasets and answer models is required before making a
generalization claim.

Second, the official DRAGON reproduction gate did not pass. The local raw
DRAGON condition changed the semantic and query-vector protocol and is useful
only as a diagnostic. A future official-reference comparison requires parity
with the pinned upstream implementation before the result can enter an
inferential table.

Third, the requested answer model name is recorded, but the provider did not
return a separately persisted actual-model identity. Future formal runs should
capture this metadata when the provider exposes it. Category 5 also retains
the frozen upstream unseeded option-order behavior, which can produce small F1
differences even when retrieved contexts are identical.

Finally, the cold/warm experiment measures the primary B condition on one
machine and one provider endpoint. The warm result assumes that the complete
conversation graph, Memory index, query-vector artifact, and question-Entity
cache already exist for the same question set. Stage timers overlap. Token
usage is directly measured, while the illustrative dollar conversion uses a
price schedule accessed after the experiment. These measurements characterize
the evaluated deployment path rather than guaranteeing latency or price on
other hardware or providers.

## Conclusion

Long-conversation question answering requires retrieval that preserves
relevant evidence without using test questions to build memory. The evaluated
Entity–Memory graph increased official evidence recall over matched dense
Memory retrieval across top-k 5–50. The same comparisons did not establish
higher overall answer F1.

Component analyses linked the retrieval difference to semantic scoring,
Entity fusion, sequence expansion, and speaker links within the declared
design. Input and sensitivity analyses bounded that result: the recall
advantage persisted under raw text, strongly reducing Entity weight lowered
recall, and no sequence-scale contrast survived correction. These findings
support a graph-based retrieval contribution on the evaluated LoCoMo set.

The contribution is best viewed as evidence that retrieval coverage and answer
quality must be measured separately. Additional datasets and a parity-qualified
official reference remain necessary before broader performance claims are
warranted. The validated cold/warm measurement quantifies the evaluated
primary condition, but broader deployment claims still require replication
across hardware and providers.
