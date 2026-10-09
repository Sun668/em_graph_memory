#!/bin/zsh
set -e
cd /Users/sun/Documents/git/graph_memory/.worktree/es-memeval-qa
source /Users/sun/Documents/git/graph_memory/env_gpt.sh
export RESEARCH_RUN_CLASS=diagnostic
export RESEARCH_PARAMETER_SNAPSHOT=/Users/sun/Documents/git/graph_memory/.worktree/es-memeval-qa/experiments/exp_2026_10_08_locomo_hipporag2/snapshots/locomo_hippo_conv47_all_v01/parameters.json
export RESEARCH_CONDITION_DIR=/Users/sun/Documents/git/graph_memory/.worktree/es-memeval-qa/outputs/locomo_hipporag2/conditions/locomo_hippo_conv47_all_v01
outputs/hipporag_venv/bin/python /Users/sun/Documents/git/graph_memory/.worktree/es-memeval-qa/experiments/exp_2026_10_08_locomo_hipporag2/run_retrieval.py --parameters /Users/sun/Documents/git/graph_memory/.worktree/es-memeval-qa/experiments/exp_2026_10_08_locomo_hipporag2/snapshots/locomo_hippo_conv47_all_v01/parameters.json
