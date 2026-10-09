# locomo_hippo_conv26_pilot02

Frozen before API calls. Mode: pilot; user: conv-26; gold is absent from the runner. If interrupted, treat the condition as diagnostic.

Completed as a **non-metric wiring/cost diagnostic**. Source, parameters, and
exact command are frozen in this directory; the small complete result is
`result.json`. It indexed only the first 20 of conv-26's 419 original dialog
turns and queried the first 3 of its 199 questions. The input dataset is
LoCoMo-10 SHA `047d8e2528126afd02ab4b6fbade825ad390447e7a91861d35960c85752b4d74`.
The extraction and fact-filter model was `gpt-3.5-turbo-0125`, embedding
`text-embedding-3-small`, temperature 0, top-k 25 (20 returned because the
pilot index has only 20 turns), max 60 chat attempts, OpenIE workers 4,
NER/triple token caps 2048/4096, two retries, linking top-k 5, damping 0.5,
passage weight 0.05. No answer or judge model was used; no F1 or judge metric
was measured. The local LoCoMo evidence recall definition was not applied to
this sub-100 pilot.

HippoRAG's upstream OpenIE extracted entities and RDF triples from each
session-time/speaker/text/caption passage. It produced 56 nodes, 122 edges,
36 entity embeddings and 47 fact embeddings. Graph construction saw only
conversation fields; question-only retrieval input was loaded after indexing;
QA answers, evidence, categories, summaries, observations, and judge data
were excluded. Retrieval used upstream query embeddings, fact filtering and
personalized PageRank over that graph, returning valid original source IDs.
There were 43 live chat calls, 17,220 input/1,506 output chat tokens, 9
embedding requests and 1,805 embedding input tokens. Elapsed time 34.0 s.
No graph or prompt component was removed after this passing pilot. Non-data
prompt scaffolds measured 554, 1,836, and 3,808 characters for NER, triples,
and fact filter respectively, all under the 5,000-character cap. This pilot
passes the graph constraint but does not count as performance evidence.
