# Cache and result migration package

Archive (generated output, not committed):

```text
outputs/migration/graph_memory_locomo_resume_2026_07_28.zip
```

- SHA-256:
  `8ab9dc388b64f2758815decf796fc28ab15e8d70e252e8c7bf1fff219617267f`
- compressed size: 66,190,646 bytes;
- uncompressed input size: approximately 97 MiB;
- entries: 64 files;
- `unzip -t`: pass;
- sorted ZIP entries exactly equal `CACHE_TRANSFER_PATHS.txt`: pass.

`CACHE_TRANSFER_PATHS.txt` is the authoritative, exhaustive repo-relative file
list. It contains:

- 10 current Memory embedding indexes shared by A/B/B-*;
- 10 current memory-only graphs and 10 current Entity–Memory graphs;
- conversation Entity, question Entity, and raw question-extraction caches;
- the immutable all-10 query artifact and its build report;
- the dependency-matched DRAGON-v3 all-10 embedding cache, manifest, and
  retrieval check needed by the later O2 diagnostic;
- the accepted corrected A and B_embed formal result directories;
- the accepted A/B_embed dense-control report.

The archive intentionally excludes obsolete graph/index variants, legacy
top-level experiment outputs, the failed B_embed run01 directory, the
`text-embedding-3-small.npz.lock` file, the absent/corrupt general text cache,
obsolete DRAGON-v2 caches, Hugging Face model weights, virtual environments,
source/data already tracked by Git, and `env_gpt.sh` or any secret.

## Restore

On the target computer, first check out the commit containing this snapshot.
To preserve the strict `output_directory_identity` of the already completed A
and B_embed formal results, use the original repository root:

```text
/Users/smsun/Documents/github/graph_memory
```

From that repository root:

```bash
unzip /path/to/graph_memory_locomo_resume_2026_07_28.zip
shasum -a 256 /path/to/graph_memory_locomo_resume_2026_07_28.zip
```

If the repository is restored under a different absolute path, the caches are
still usable for new runs, but the immutable A/B_embed run configs continue to
record their original absolute output directories. The strict validator and
significance loader will correctly flag those migrated historical conditions
as relocated. Do not edit their JSON files. Either restore at the original
path or rerun A under the new root before the final corrected A/B significance
analysis.

After restoration, configure the target machine's own `env_gpt.sh`; it is not
in the archive. Before the next metric run, verify the archive hash, all 64
paths, the query artifact SHA, 69 tests, 16 vendor hashes, and absence of the
general writable context cache.
