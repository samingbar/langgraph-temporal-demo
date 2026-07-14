# LangGraph + Temporal Support-Agent Demo

## Run the demo

Prerequisites: Docker, the [Temporal CLI](https://docs.temporal.io/cli), and
[`uv`](https://docs.astral.sh/uv/). From the repository root:

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY or OPENAI_API_KEY.
make up
```

Open the chat UI at <http://localhost:5173>. Use the start-screen selector to
compare all three agent implementations. The Temporal UI is available at
<http://localhost:8233> for the two durable variants.

```bash
make status   # Show which services and local processes are running.
make logs     # Tail Temporal, worker, API, and web logs.
make down     # Stop everything started by make up.
```

To run one implementation instead of the full comparison stack:

```bash
make original             # Original Temporal workflow
make langgraph            # Standalone, in-memory LangGraph
make temporal-langgraph   # LangGraph backed by a Temporal workflow
```

Try the durability demonstration with `make kill-worker`, then restart the
corresponding worker with `make worker` or `make temporal-langgraph-worker`.
The Temporal-backed conversation resumes from persisted workflow history.

## What this repository demonstrates

The demo implements a music-store customer-support agent that searches a
PostgreSQL copy of the Chinook catalog, reviews customer orders, and pauses for
human approval before purchases. Three implementations share the same browser
experience and HTTP contract:

- `python/` — a hand-written Temporal workflow and Activities.
- `python-langgraph/` — standalone LangGraph with process-local state.
- `python-langgraph-temporal/` — LangGraph nodes executed through Temporal.
- `web/` — dependency-free browser UI with backend selection and approval UI.
- `db/` — Chinook schema, catalog data, and the seeded demo customer.

## Demo controls

The Makefile includes failure/recovery controls used during presentations:

```bash
make kill-worker                     # Stop the original Temporal worker.
make kill-temporal-langgraph-worker  # Stop the LangGraph + Temporal worker.
make kill-db                         # Stop Postgres during a tool call.
make db                              # Restart Postgres.
```

Stopping a worker demonstrates durable execution: the workflow remains in
Temporal and continues when a compatible worker returns. Stopping the database
demonstrates the difference between transient infrastructure failures and
model-visible business errors.

## Configuration

Copy `.env.example` to `.env` and configure one supported model provider.
Important variables include:

| Variable | Purpose |
| --- | --- |
| `LLM_PROVIDER` | Select `anthropic` or `openai`. |
| `ANTHROPIC_API_KEY` | Credential used by the Anthropic adapter. |
| `OPENAI_API_KEY` | Credential used by the OpenAI adapter. |
| `ANTHROPIC_MODEL` / `OPENAI_MODEL` | Override the provider's default model. |
| `DB_URL` | Override the local Chinook PostgreSQL connection. |
| `TEMPORAL_ADDRESS` | Override the local Temporal endpoint. |
| `OPENAI_FAILURE_RATE` | Inject planning failures for retry demonstrations. |

Do not commit `.env`; it is intentionally ignored by Git.

## Manual operation and troubleshooting

The one-command path is recommended. For individual frontend/backend commands,
port overrides, and troubleshooting, see [web/README.md](web/README.md). Each
Python implementation also contains a `starter.py` terminal client and an
`approve.py` approval helper.
