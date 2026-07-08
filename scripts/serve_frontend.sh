#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# serve_frontend.sh - build the React/Vite SPA and serve the static bundle.
#
# Builds frontend/dist and serves it on port 5173 bound to 0.0.0.0.
#
# IMPORTANT - /api proxying:
#   The built SPA calls `/api/...`. A plain static file server does NOT proxy
#   those calls to the FastAPI backend (which serves routes at ROOT on :8000,
#   no /api prefix). This script serves static files only.
#
#   For a setup that ALSO reverse-proxies /api -> http://localhost:8000
#   (stripping the /api prefix), use one of:
#     * main.ipynb  - its frontend cell runs a tiny inline Python proxy
#                     (static files + /api -> :8000) on port 5173.
#     * docker compose -f docker-compose.prod.yml up
#                     - nginx serves the SPA AND proxies /api -> backend:8000.
#
#   So: use THIS script when you have an external proxy/ingress in front, or
#   when you only need to smoke-test the static build. For a real deployment
#   prefer the prod docker/nginx path documented in docs/deployment.md.
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
PORT="${PORT:-5173}"

echo "==> Frontend directory: ${FRONTEND_DIR}"
cd "${FRONTEND_DIR}"

echo "==> Installing Node dependencies (npm install)"
npm install

echo "==> Building production bundle (npm run build -> dist/)"
npm run build

echo "==> Serving dist/ on http://0.0.0.0:${PORT}"
echo "    NOTE: this is a STATIC server with NO /api proxy."
echo "    See the header of this script for proxied alternatives."

# Prefer `npx serve` (SPA history routing). Use Python's http.server when npx serve is unavailable.
if command -v npx >/dev/null 2>&1; then
  exec npx --yes serve -s dist -l "tcp://0.0.0.0:${PORT}"
else
  cd dist
  exec python3 -m http.server "${PORT}" --bind 0.0.0.0
fi