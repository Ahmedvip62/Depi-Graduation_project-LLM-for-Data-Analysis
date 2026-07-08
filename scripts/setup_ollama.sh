#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_ollama.sh - install Ollama, start the server, and pull the exact
# models the Universal Analyst backend expects.
#
# Idempotent: safe to re-run. It skips work that is already done.
#
# Models:
#   MAIN   : gemma4:12b
#   ROUTER : gemma4:e4b
# ---------------------------------------------------------------------------
set -euo pipefail

OLLAMA_HOST_URL="${OLLAMA_HOST:-http://localhost:11434}"

ensure_model() {
  local label="$1"
  local model="$2"
  echo "    Pulling ${label}: ${model} ..."
  ollama pull "${model}"
  echo "    ${label} ready: ${model}"
}

echo "==> Ensuring Ollama is installed"
if ! command -v ollama >/dev/null 2>&1; then
  echo "    Ollama not found. Installing..."
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "    Ollama already installed: $(ollama --version 2>/dev/null || echo unknown)"
fi

echo "==> Ensuring Ollama server is running"
if curl -fsS "${OLLAMA_HOST_URL}/api/tags" >/dev/null 2>&1; then
  echo "    Ollama server already responding at ${OLLAMA_HOST_URL}"
else
  echo "    Starting 'ollama serve' in the background (log: /tmp/ollama.log)"
  nohup ollama serve > /tmp/ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    if curl -fsS "${OLLAMA_HOST_URL}/api/tags" >/dev/null 2>&1; then
      echo "    Ollama server is ready."
      break
    fi
    sleep 1
  done
fi

MAIN_MODEL="gemma4:12b"
ROUTER_MODEL="gemma4:e4b"

echo "==> Pulling required models"
ensure_model MAIN "${MAIN_MODEL}"
ensure_model ROUTER "${ROUTER_MODEL}"

echo ""
echo "==================== Ollama setup summary ===================="
echo "  MAIN model   : ${MAIN_MODEL}"
echo "  ROUTER model : ${ROUTER_MODEL}"
echo "=============================================================="
echo ""
echo "Export these for the backend if they differ from the defaults:"
echo "  export MODEL_NAME=${MAIN_MODEL}"
echo "  export ROUTER_MODEL_NAME=${ROUTER_MODEL}"
echo ""
echo "Ollama setup complete."