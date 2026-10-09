# Frozen index preflight failure

The first `prepare_indexes.py` launch failed before any Memory embedding requests or output file. The query artifact was correctly bound to `questions.json` but the retrieval/index runner requires the SHA-256 of `retrieval_inputs.json`. Their ordered 1,427 question records are identical; their file SHA-256 differs because retrieval inputs also carry the conversations. The frozen `v04_memory_indexes_frozen/parameters.json` remains an invalid attempted condition and is not reused.

The question-only artifact remains valid for its original dataset and is preserved. A new, separately hashed artifact will be constructed from exactly the same vectors only after byte-for-byte ordered question-record parity is proven, then bound to the retrieval input SHA-256. No model vectors are regenerated or silently changed. Source at this failure is `snapshots/v01_preflight_frozen/`; no A/B metric has run.
