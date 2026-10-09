# ChatStack

A full-stack AI chat app that runs with Docker Compose or on Kubernetes: a React UI, a FastAPI backend, Postgres for conversation memory, and a local LLM served by Ollama.

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
- **Kubernetes deployment**: the same stack as Deployments, Services, PVCs, a ConfigMap, a Secret and a Job, with probes, a `Recreate` strategy for stateful pods, and self-healing

## Run on Kubernetes

The same images run on Kubernetes (tested on Docker Desktop's built-in single-node cluster) with no code changes. The manifests are in `k8s/`.

```bash
cp .env.example .env                        # then set DB_PASSWORD
docker compose build                        # build the backend and frontend images
docker tag chatstack-backend:latest  chatstack-backend:v1
docker tag chatstack-frontend:latest chatstack-frontend:v1
kubectl create secret generic db-secret --from-env-file=.env
kubectl apply -f k8s/
kubectl logs -f job/ollama-pull             # one-time model download (~1.3 GB)
```

Open http://localhost:30080.

The images are tagged `v1` because with `:latest` Kubernetes always tries to pull from a registry, where these locally built images don't exist. The password is created as a Secret from `.env` by command, so it is never written into a manifest.

| Compose | Kubernetes |
|---|---|
| `.env` | Secret `db-secret` |
| `db` + `db-data` volume + healthcheck | PVC + Deployment (`Recreate`, readiness probe `pg_isready`) + ClusterIP Service |
| `ollama` + `ollama-models` volume | PVC + Deployment (`Recreate`) + ClusterIP Service |
| `ollama-init` | Job (runs once to completion) |
| `backend` + `environment:` | ConfigMap + Secret reference + readiness/liveness probes on `/health` + ClusterIP Service |
| `frontend` + `ports: "8080:80"` | Deployment (2 replicas) + NodePort Service on `30080` |

Because the Services keep the Compose names (`db`, `ollama`, `backend`), nginx and the backend reach each other exactly as before.

Stop the app but keep chat history and the model:

```bash
kubectl delete deployment frontend backend ollama db
```

Remove everything, including the data: `kubectl delete -f k8s/ && kubectl delete secret db-secret`

## Project structure

```
chatstack/
├── backend/        FastAPI app, Dockerfile, .dockerignore
├── frontend/       React (Vite) app, nginx.conf, multi-stage Dockerfile
├── k8s/            Kubernetes manifests (db, ollama, ollama-pull Job, backend, frontend)
├── compose.yaml
└── .env.example
```

## Notes

- On macOS, Docker can't use the Apple GPU, so the model runs on CPU. The small 1B model keeps answers to a few seconds, at the cost of accuracy.
- To try a different model, change `MODEL` and the `ollama pull` tag in `compose.yaml`.
- Reset everything (including history and the model): `docker compose down -v`