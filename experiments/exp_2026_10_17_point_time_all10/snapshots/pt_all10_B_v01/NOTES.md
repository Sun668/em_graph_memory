# Frozen B control before generation

The plugin freeze passed before any all-ten answer call. Frozen parameter
SHA-256: `33e5882bd8be37f849a86c0a023af2824203c4ac99acf8e4fef2bd9d3783813a`.
Canonical command SHA-256:
`893e7b1c15f476719a481980e3f1bd61ccf393829330c6306857fe4c0f8a856b`.
The secret-free exact command is in `command.txt`; API variables are sourced
from the user-approved root `env_gpt.sh`. Source is committed at the base
recorded in `parameters.json`; no answer output directory exists yet. This
condition retains raw B Reader text. Graph construction uses conversation
data only, QA recall uses the graph, and the treatment adds zero prompt
scaffold. Answer F1 and model use are unobserved at this snapshot.
