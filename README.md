# ChatStack

A full-stack AI chat app that runs entirely in Docker with one command: a React UI, a FastAPI backend, Postgres for conversation memory, and a local LLM served by Ollama.

## Architecture

```
Browser ──:8080──► frontend (nginx + React)
                      └── /api/* ──► backend (FastAPI)
                                       ├──► db (Postgres)       → volume: db-data
                                       └──► ollama (llama3.2:1b) → volume: ollama-models
```

Only the frontend is exposed. The backend, database and LLM are reachable only inside the Compose network.

## Quick start

```bash
git clone https://github.com/PrathibhaDevkar/chatstack.git
cd chatstack
cp .env.example .env        # then set DB_PASSWORD
docker compose up -d
```

Open http://localhost:8080. The first start downloads the model (~1.3 GB); follow it with `docker compose logs -f ollama-init`.

## What it demonstrates

- **Multi-stage build**: the frontend is compiled with Node, then served from `nginx:alpine` (final image ≈ 93 MB vs. 194 MB for Node alone)
- **Reverse proxy**: nginx serves the UI and forwards `/api/*` to the backend, so there's one entry point and no CORS
- **Healthchecks**: the backend waits for Postgres to be ready (`pg_isready`), not just started
- **Init container**: `ollama-init` pulls the model once, then exits
- **Persistent volumes**: chat history and model weights survive `docker compose down`
- **Config via environment variables**: secrets live in `.env`; the model is swappable via `MODEL`
- **Cache-friendly Dockerfiles** and `.dockerignore` files

## Project structure

```
chatstack/
├── backend/        FastAPI app, Dockerfile, .dockerignore
├── frontend/       React (Vite) app, nginx.conf, multi-stage Dockerfile
├── compose.yaml
└── .env.example
```

## Notes

- On macOS, Docker can't use the Apple GPU, so the model runs on CPU. The small 1B model keeps answers to a few seconds, at the cost of accuracy.
- To try a different model, change `MODEL` and the `ollama pull` tag in `compose.yaml`.
- Reset everything (including history and the model): `docker compose down -v`