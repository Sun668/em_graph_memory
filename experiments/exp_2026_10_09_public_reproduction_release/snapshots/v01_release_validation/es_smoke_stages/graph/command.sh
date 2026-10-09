#!/bin/sh
set -eu
export RESEARCH_RUN_CLASS=diagnostic
export RESEARCH_PARAMETER_SNAPSHOT=/Users/sun/Documents/git/em_graph_memory/outputs/reproduction_release_v109/es_live_smoke/snapshots/graph/parameters.json
export RESEARCH_CONDITION_DIR=/Users/sun/Documents/git/em_graph_memory/outputs/reproduction_release_v109/es_live_smoke/conditions/graph
/Users/sun/Documents/git/graph_memory/.venv/bin/python /Users/sun/Documents/git/em_graph_memory/experiments/exp_2026_10_08_es_memeval_full_ab/build_b_graphs.py --run-id release_v109_smoke_graph --parameter-snapshot /Users/sun/Documents/git/em_graph_memory/outputs/reproduction_release_v109/es_live_smoke/snapshots/graph/parameters.json --data-file /Users/sun/Documents/git/em_graph_memory/outputs/reproduction_release_v109/es_live_smoke/graph.json --cache-dir /Users/sun/Documents/git/em_graph_memory/outputs/reproduction_release_v109/es_live_smoke/cache --extract-model gpt-3.5-turbo-0125 --output-dir /Users/sun/Documents/git/em_graph_memory/outputs/reproduction_release_v109/es_live_smoke/conditions/graph --workers 2
