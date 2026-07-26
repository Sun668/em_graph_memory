# Copy to env.sh and fill secrets. Never commit env.sh.
export OUT_DIR=./outputs
export EMB_DIR=./outputs
export DATA_FILE_PATH=./data/locomo10.json

export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1

# Matched publish stack
export OPENAI_MODEL=gpt-3.5-turbo
export MODEL=gpt-3.5-turbo
export JUDGE_MODEL=gpt-3.5-turbo
export EM_GRAPH_EMBED_MODEL=text-embedding-3-small

# Optional throughput knobs
export EM_GRAPH_EMBED_WAIT=0.05
export EM_GRAPH_MAX_WORKERS=8
export EM_GRAPH_ANSWER_RESUME=1
