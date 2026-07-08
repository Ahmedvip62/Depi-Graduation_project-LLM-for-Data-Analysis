# Universal Analyst - Deployment Guide

Run Universal Analyst on Lightning.ai or any Linux NVIDIA GPU cloud environment.

## Requirements

- Linux runtime, preferably Ubuntu 22.04 or newer.
- Python 3.12.
- Node.js 20.
- Ollama with required tags: `gemma4:12b` and `gemma4:e4b`.
- NVIDIA GPU with enough VRAM for the selected Gemma 4 tags.

## Option A - One-Click Notebook

1. Upload the copied project.
2. Open `main.ipynb`.
3. Run all cells.
4. Use the forwarded `:5173` URL for the frontend.
5. Use the forwarded `:8000/docs` URL for API docs.

The notebook installs missing dependencies, starts Ollama, pulls the exact required model tags, starts FastAPI on `:8000`, and serves the built frontend on `:5173` with `/api` proxying.

## Option B - Docker Compose

The compose files expect Ollama to run on the host and reach it through `host.docker.internal`.

```bash
bash scripts/setup_ollama.sh
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f
```

Backend environment values can be overridden with:

```bash
export OLLAMA_HOST=http://host.docker.internal:11434
export MODEL_NAME=gemma4:12b
export ROUTER_MODEL_NAME=gemma4:e4b
export ALLOWED_ORIGINS=http://localhost,http://localhost:5173
```

## Ports

- `:5173` - frontend app in notebook/dev mode.
- `:8000` - FastAPI backend and `/docs`.
- `:80` - production nginx frontend when using `docker-compose.prod.yml`.

## Verification In Cloud

After startup, check:

1. Upload a dataset and confirm the dashboard opens.
2. Ask a generic question such as `what is this dataset about?`.
3. Ask `generate dashboard for this dataset` and confirm new charts appear.
4. Attach an image in chat and submit a prompt.
5. Use the PDF button and confirm a downloadable report is returned.