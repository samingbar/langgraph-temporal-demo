# LangGraph Temporal Demo

This repository contains three versions of the same music-store support-agent
demo:

- `python/`: original Temporal workflow implementation.
- `python-langgraph/`: standalone LangGraph implementation.
- `python-langgraph-temporal/`: Temporal + LangGraph integration demo.

The deployable Demo Cloud shape runs all three variants behind one comparison
UI. The source stays in this repository. Demo Cloud onboarding adds one YAML
definition to `tmprl-demo-cloud-registry/projects/demo/<demo-slug>.yaml`; it
does not move this app source into the registry repository.

Instruqt is not involved in this deployment path. If an Instruqt version is
needed later, treat it as a separate registry onboarding under the registry's
Instruqt path.

## Deployable Components

| Component | Purpose | Command | Port | Dockerfile | Public ingress |
| --- | --- | --- | --- | --- | --- |
| `temporal-api` | Original Temporal HTTP gateway | `python -m uvicorn api:app --host 0.0.0.0 --port 8000` | `8000` | `docker/temporal.Dockerfile` | via web proxy |
| `temporal-worker` | Original Temporal workflow/activity worker | `python worker.py` | none | `docker/temporal.Dockerfile` | no |
| `langgraph-api` | Standalone, in-process LangGraph agent | `python -m uvicorn api:app --host 0.0.0.0 --port 8001` | `8001` | `docker/langgraph.Dockerfile` | via web proxy |
| `temporal-langgraph-api` | Temporal + LangGraph HTTP gateway | `python -m uvicorn api:app --host 0.0.0.0 --port 8002` | `8002` | `docker/backend.Dockerfile` | via web proxy |
| `temporal-langgraph-worker` | Temporal worker registering `LangGraphPlugin` and workflow code | `python worker.py` | none | `docker/backend.Dockerfile` | no |
| `web` | Static chat UI | `nginx -g 'daemon off;'` | `8080` | `docker/frontend.Dockerfile` | yes |
| `postgres` | Shared Chinook catalog/order database | PostgreSQL entrypoint | `5432` | `docker/postgres.Dockerfile` | no |

Each Temporal API/worker pair shares an image and runs different commands. The
web container proxies stable `/api/temporal`, `/api/langgraph`, and
`/api/temporal-langgraph` paths to the private services.

## Required Runtime Configuration

Production values should be provided by the registry/operator environment or
secret mechanism:

- `TEMPORAL_ADDRESS`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_TLS`
- `TEMPORAL_API_KEY` or `TEMPORAL_TLS_CERT` plus `TEMPORAL_TLS_KEY`, when using Temporal Cloud
- `TEMPORAL_TASK_QUEUE`
- `LANGGRAPH_TEMPORAL_TASK_QUEUE`
- `DB_URL`
- `LLM_PROVIDER`
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- `ANTHROPIC_MODEL` or `OPENAI_MODEL`
- `CORS_ALLOW_ORIGINS`
- `DEMO_ACCESS_TOKEN` and `DEMO_AUTH_REQUIRED=true`

Frontend container variables:

- `DEFAULT_AGENT_BACKEND`
- `TEMPORAL_BACKEND_URL`
- `LANGGRAPH_BACKEND_URL`
- `TEMPORAL_LANGGRAPH_BACKEND_URL`
- `TEMPORAL_UI_URL`

`DEMO_ACCESS_TOKEN` is the lightweight public-demo gate. When it is set, each API
requires either `X-Demo-Token: <token>` or `Authorization: Bearer <token>` on
conversation endpoints. Set `DEMO_AUTH_REQUIRED=true` in public deployments so
each API refuses to start without a token. The web UI accepts a token once from
`?token=<token>` or `?access_token=<token>`, removes it from the URL, and keeps
it only for the browser session. Leave both settings unset only for local development.

## Local Quick Start

Copy `.env.example` to `.env` and set either `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY`.

Start the full local stack:

```bash
make up
```

Open:

```text
http://localhost:5173?backend=temporal-langgraph
```

Stop everything the Makefile started:

```bash
make down
```

## Manual Local Commands

Start Postgres:

```bash
docker compose up -d
```

Start a local Temporal dev server:

```bash
temporal server start-dev --ui-port 8233
```

Start the Temporal + LangGraph worker:

```bash
cd python-langgraph-temporal
uv run python worker.py
```

Start the Temporal + LangGraph API:

```bash
cd python-langgraph-temporal
uv run python -m uvicorn api:app --port 8002
```

Start the web UI:

```bash
cd web
python3 -m http.server 5173
```

## Docker Builds

Build the three Python implementation images from the repo root:

```bash
docker build -f docker/temporal.Dockerfile -t langgraph-temporal-demo-temporal .
docker build -f docker/langgraph.Dockerfile -t langgraph-temporal-demo-langgraph .
docker build -f docker/backend.Dockerfile -t langgraph-temporal-demo-temporal-langgraph .
```

Build the frontend image:

```bash
docker build -f docker/frontend.Dockerfile -t langgraph-temporal-demo-web .
docker build -f docker/postgres.Dockerfile -t langgraph-temporal-demo-postgres .
```

For example, run the Temporal + LangGraph API locally with Docker, assuming
Temporal and Postgres are reachable from the container network:

```bash
docker run --rm -p 8002:8002 --env-file .env \
  langgraph-temporal-demo-temporal-langgraph
```

Run its worker with the same image:

```bash
docker run --rm --env-file .env \
  langgraph-temporal-demo-temporal-langgraph python worker.py
```

Run the frontend:

```bash
docker run --rm -p 8080:8080 \
  -e WEB_PORT=8080 \
  -e DEFAULT_AGENT_BACKEND=temporal-langgraph \
  -e TEMPORAL_BACKEND_URL=http://localhost:8000 \
  -e LANGGRAPH_BACKEND_URL=http://localhost:8001 \
  -e TEMPORAL_LANGGRAPH_BACKEND_URL=http://localhost:8002 \
  langgraph-temporal-demo-web
```

For production, do not use `localhost` or `host.docker.internal` for
`TEMPORAL_ADDRESS`, `DB_URL`, or backend URLs. Provide routable service names or
managed service endpoints through the registry YAML/environment.

## Demo Cloud Registry

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for the complete deployment-readiness,
secret-provisioning, validation, and onboarding procedure.

This repo includes a source-controlled `DemoProject` declaration at
`demo-cloud/langgraph-temporal-demo.yaml`. After completing the readiness
checklist, copy it into:

```text
tmprl-demo-cloud-registry/projects/demo/langgraph-temporal-demo.yaml
```

The application source remains in this repository. Instruqt is a separate,
optional onboarding path and is not required for this deployment.
