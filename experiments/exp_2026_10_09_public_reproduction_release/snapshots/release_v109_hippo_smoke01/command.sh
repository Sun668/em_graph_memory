#!/bin/zsh
set -e
cd /Users/sun/Documents/git/em_graph_memory
: ${OPENAI_API_KEY:?Export OPENAI_API_KEY before running}
export OPENAI_BASE_URL=https://api.openai.com/v1
export RESEARCH_RUN_CLASS=diagnostic
export RESEARCH_PARAMETER_SNAPSHOT=/Users/sun/Documents/git/em_graph_memory/experiments/exp_2026_10_09_public_reproduction_release/snapshots/release_v109_hippo_smoke01/parameters.json
export RESEARCH_CONDITION_DIR=/Users/sun/Documents/git/em_graph_memory/outputs/reproduction_release_v109/hippo_conditions/release_v109_hippo_smoke01
/Users/sun/Documents/git/graph_memory/.worktree/es-memeval-qa/outputs/hipporag_venv/bin/python /Users/sun/Documents/git/em_graph_memory/experiments/exp_2026_10_08_locomo_hipporag2/run_retrieval.py --parameters /Users/sun/Documents/git/em_graph_memory/experiments/exp_2026_10_09_public_reproduction_release/snapshots/release_v109_hippo_smoke01/parameters.json
