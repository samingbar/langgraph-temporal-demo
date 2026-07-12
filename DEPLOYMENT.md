# Demo Cloud deployment readiness

This guide covers deploying all three implementations of the support-agent demo
to Temporal's shared Demo Cloud and adding the comparison to the demo registry:

- the original Temporal workflow;
- standalone LangGraph; and
- Temporal + LangGraph integration.

The short version is:

1. Keep the application source in this repository.
2. Make the application container- and environment-driven now.
3. Move or mirror the finished source repository into the `temporal-sa` GitHub
   organization.
4. Add one `DemoProject` YAML file to
   `tmprl-demo-cloud-registry/projects/demo/`.
5. Let Flux and the registry operator build and deploy it.

Instruqt is **not** required. It is a separate registry resource type used only
when an Instruqt course should also be managed.

## What lives where

| Item | Owner/location |
| --- | --- |
| Python, web, SQL, Dockerfiles, and tests | This source repository |
| Demo declaration | `tmprl-demo-cloud-registry/projects/demo/langgraph-temporal-demo.yaml` |
| Container builds and ECR repositories | Created by the registry operator |
| Kubernetes namespace, workloads, Services, and ingress | Created by the registry operator |
| Temporal Cloud namespace and API key | Created and rotated by the registry operator |
| LLM key, database credentials, and demo access token | Project-owned AWS Secrets Manager values |
| Instruqt track | Not part of this deployment |

The platform derives resource names from `metadata.name`. Do not add Kubernetes
manifests, Helm charts, Flux overlays, ECR repositories, or a Temporal namespace
to this repository for the supported onboarding path.

## When to do the refactor

Design for deployment before polishing the demo:

- keep every API and worker, the shared UI, and the database runnable as
  containers;
- move deployment-specific values to environment variables;
- keep the Temporal APIs and workers stateless, and explicitly keep standalone
  LangGraph at one replica because its comparison state is in-process;
- keep LLM and access credentials out of source and image layers; and
- expose a cheap HTTP health endpoint.

Wait until the demo flow and container smoke tests are stable before opening the
registry pull request. The registry file is small, but it is much easier to
review when the source repository and its Docker build contract have stopped
moving.

## 1. Finish the deployable application shape

Deploy all three source directories. They share one UI and one seeded database,
while each implementation keeps its own runtime process and state model:

| Variant | Source | Runtime components |
| --- | --- | --- |
| Original Temporal | `python/` | API + Temporal worker |
| Standalone LangGraph | `python-langgraph/` | API only |
| Temporal + LangGraph | `python-langgraph-temporal/` | API + Temporal worker |

The current repository already has:

- one reusable Temporal + LangGraph image in `docker/backend.Dockerfile`;
- separate API and worker commands for both Temporal-backed variants;
- a frontend image in `docker/frontend.Dockerfile`;
- configuration through environment variables;
- `GET /healthz` and a `DEMO_ACCESS_TOKEN` gate on the Temporal + LangGraph API;
  and
- a frontend selector already capable of listing all three backends.

Complete these deployment-specific items before onboarding:

### Add a database image

Local Compose mounts the SQL files from the host, which the registry will not
do. Add `docker/postgres.Dockerfile` so the seed data is part of an immutable
image:

```dockerfile
FROM postgres:16

COPY db/chinook.sql /docker-entrypoint-initdb.d/01-chinook.sql
COPY db/demo-customer.sql /docker-entrypoint-initdb.d/02-demo-customer.sql
```

The registry manifest can then deploy `postgres` as a private component with a
stable `postgres:5432` service address.

### Add one image per Python implementation

The registry build contract does not select different source subdirectories
from one parameterized Dockerfile. Keep the existing
`docker/backend.Dockerfile` for `python-langgraph-temporal/` and add:

- `docker/temporal.Dockerfile` for `python/`; and
- `docker/langgraph.Dockerfile` for `python-langgraph/`.

Each image should follow the existing backend pattern: copy
`support-agent-common/`, install the matching `pyproject.toml` and lockfile with
`uv sync --frozen --no-dev`, then copy that implementation's source. The
original Temporal image is reused by its API and worker; the Temporal +
LangGraph image is reused by its API and worker.

Do not combine the three Python environments into one image. Separate builds
make dependency differences visible and let the operator roll each variant
independently.

### Use one public origin

Demo Cloud assigns one public subdomain. Make the web Nginx container the only
public service and have it reverse-proxy these same-origin paths:

- `/api/temporal/*` to the original Temporal API service;
- `/api/langgraph/*` to the standalone LangGraph API service;
- `/api/temporal-langgraph/*` to the Temporal + LangGraph API service;
- `/healthz` to a backend health endpoint; and
- all other paths to the static comparison UI.

Update `docker/nginx-default.conf.template` with those proxy locations and
strip the corresponding `/api/<variant>/` prefix when forwarding. Set the
frontend variables to relative paths:

```text
TEMPORAL_BACKEND_URL=/api/temporal
LANGGRAPH_BACKEND_URL=/api/langgraph
TEMPORAL_LANGGRAPH_BACKEND_URL=/api/temporal-langgraph
```

The proxy shape is:

```nginx
location /api/temporal/ {
    proxy_pass http://temporal-api:8000/;
}

location /api/langgraph/ {
    proxy_pass http://langgraph-api:8001/;
}

location /api/temporal-langgraph/ {
    proxy_pass http://temporal-langgraph-api:8002/;
}

location = /healthz {
    proxy_pass http://temporal-langgraph-api:8002/healthz;
}
```

The trailing slash on each `proxy_pass` is what removes the public prefix.
Retain the usual forwarded-host/protocol headers and pass
`X-Demo-Token`/`Authorization` through unchanged.

The existing backend selector then switches implementations without changing
pages, hosts, or access tokens. No API component needs direct public ingress.

The frontend currently builds Temporal UI workflow links even when
`TEMPORAL_UI_URL` is empty. Before deployment, change it to omit those links
when no Cloud UI URL is configured. A Cloud UI URL may be added later once the
operator has created the namespace and its full namespace ID is known.

### Apply the same public-demo controls to all APIs

The original Temporal and standalone LangGraph APIs do not yet have the access
gate or `/healthz` endpoint implemented by `python-langgraph-temporal/api.py`.
Add the same behavior to both before deployment:

- require `X-Demo-Token` or `Authorization: Bearer` on every conversation and
  approval endpoint when `DEMO_ACCESS_TOKEN` is set;
- fail startup when `DEMO_AUTH_REQUIRED=true` and the token is missing; and
- expose an unauthenticated, side-effect-free `GET /healthz`.

This matters most for standalone LangGraph because the API process itself calls
the LLM. The outer Demo Cloud ingress authentication and the application token
should both remain enabled.

### Keep production configuration in environment variables

All three APIs need:

- `DEMO_AUTH_REQUIRED=true`
- `DEMO_ACCESS_TOKEN` from a project secret

The original Temporal API and worker should read a shared
`TEMPORAL_TASK_QUEUE=support-agent` value instead of relying on a hard-coded
queue. The Temporal + LangGraph API and worker use
`LANGGRAPH_TEMPORAL_TASK_QUEUE=support-agent-temporal-langgraph`.

Both Temporal workers and the standalone LangGraph API need:

- `LLM_PROVIDER=anthropic` (or `openai`)
- the selected provider's API key from a project secret
- `DB_URL` from a project secret

Do not manually configure Temporal credentials in the registry file. Mark the
two Temporal APIs with `temporalAccess: true` and both workers with
`worker: true`; the operator injects `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`,
`TEMPORAL_API_KEY`, and `TEMPORAL_TLS` into those four components. The standalone
LangGraph API receives no Temporal credentials.

Keep the standalone LangGraph API at one replica. Its conversation store is
in-process, so scaling it horizontally would make conversations depend on which
pod receives the request.

### Rebase and test the intended source

Rebase or merge the upstream demo changes before freezing the deployment
contract. Then run:

```bash
make test
docker build -f docker/temporal.Dockerfile -t langgraph-temporal-demo-temporal .
docker build -f docker/langgraph.Dockerfile -t langgraph-temporal-demo-langgraph .
docker build -f docker/backend.Dockerfile -t langgraph-temporal-demo-temporal-langgraph .
docker build -f docker/frontend.Dockerfile -t langgraph-temporal-demo-web .
docker build -f docker/postgres.Dockerfile -t langgraph-temporal-demo-postgres .
```

Also run the complete demo locally and verify the selector can run the same
conversation, tool-use, and approval flow against all three variants. Verify
worker restart/recovery on both Temporal-backed variants and confirm that the
standalone LangGraph behavior provides the intended durability contrast.

## 2. Put the source under `temporal-sa`

The registry schema accepts source repositories in the `temporal-sa` GitHub
organization. Transfer this repository or create the final repository there,
for example:

```text
https://github.com/temporal-sa/langgraph-temporal-demo
```

The source may be public or private. The platform uses its shared read-only
GitHub credential for repositories in that organization. Keep the build
contexts and Dockerfile paths in the repository root exactly as declared in the
registry YAML.

## 3. Create the project-owned secrets

The operator creates Temporal credentials, but it does not invent application
secrets. Before the first successful deployment, create these AWS Secrets
Manager JSON values:

```text
tmprl-dem-cld/langgraph-temporal-demo/llm-credentials
tmprl-dem-cld/langgraph-temporal-demo/database
tmprl-dem-cld/langgraph-temporal-demo/demo-access
```

Suggested JSON shapes:

```json
{
  "ANTHROPIC_API_KEY": "..."
}
```

```json
{
  "POSTGRES_USER": "demo",
  "POSTGRES_PASSWORD": "...",
  "DB_URL": "postgresql://demo:<url-encoded-password>@postgres:5432/chinook"
}
```

```json
{
  "DEMO_ACCESS_TOKEN": "a-long-random-value"
}
```

If OpenAI is selected instead, require `OPENAI_API_KEY` in the manifest and set
`LLM_PROVIDER=openai`. Use a URL-encoded database password in `DB_URL`.

Share demo links as
`https://langgraph-temporal-demo.tmprl-demo.cloud/?token=<value>`. The frontend
removes the token from the URL and retains it only in browser session storage.
The platform's ingress authentication should remain enabled as an additional
outer control.

## 4. Add the registry declaration

Use the maintained copy in
`demo-cloud/langgraph-temporal-demo.yaml`. After the source repository and
Dockerfiles are ready, copy that one file into the registry repository:

```text
tmprl-demo-cloud-registry/projects/demo/langgraph-temporal-demo.yaml
```

Do not copy this source tree into the registry and do not add a directory-level
`kustomization.yaml`. Flux automatically includes the plain YAML resources in
`projects/demo/`.

Before opening the registry PR, replace any repository name or provider choice
that differs from the final source. Catalog values such as `temporalSdks` are
metadata only; they do not install SDKs or affect the deployment.

## 5. Validate and open the registry PR

From a checkout of `tmprl-demo-cloud-registry`, run its current validator:

```bash
uv run --isolated --with jsonschema --with pyyaml \
  python scripts/validate_projects.py
```

Commit only the new `projects/demo/langgraph-temporal-demo.yaml` file and open a
pull request. The registry CI validates the CRD schema and cross-project rules.

After merge, Flux applies the `DemoProject` resource and the operator:

1. creates `tmprl-dem-cld-langgraph-temporal-demo` resources;
2. creates the ECR repositories and builds the declared images;
3. creates a Temporal Cloud namespace and namespace-scoped API key;
4. syncs the declared project secrets;
5. deploys Postgres, two Temporal workers, three APIs, and the web component;
6. creates the `langgraph-temporal-demo.tmprl-demo.cloud` TLS route; and
7. promotes the candidate after pods are ready and `/healthz` returns 200.

Watch the `DemoProject` status and registry catalog for build, external-secret,
rollout, and smoke-check failures. A missing user-managed secret is expected to
block readiness until its JSON value and required keys exist.

## 6. Deployment acceptance checklist

- [ ] Final source is rebased/merged and hosted under `temporal-sa`.
- [ ] All five Docker images build from a clean checkout.
- [ ] No secrets are committed or copied into an image.
- [ ] Each Temporal API and its worker use the same task queue.
- [ ] Both Temporal APIs start with operator-injected Cloud credentials.
- [ ] Both workers poll and complete a test workflow.
- [ ] Postgres initializes Chinook and the demo customer once.
- [ ] The UI selector exposes all three variants without a page or host change.
- [ ] All API calls use same-origin `/api/<variant>` paths.
- [ ] Access-token handling protects all three APIs.
- [ ] `/healthz` and every backend health endpoint return 200 through Nginx.
- [ ] Purchase approval works in all three variants.
- [ ] Worker-restart recovery works in both Temporal-backed variants.
- [ ] The standalone process-state limitation is easy to demonstrate safely.
- [ ] Registry validator and CI pass.
- [ ] Catalog title, summary, tags, and SDK metadata are correct.
- [ ] Runbook, deck, speaker notes, and recording links are added to
      `spec.registry` when those assets are ready.

## Instruqt, later if needed

An Instruqt course is a separate `InstruqtCourse` resource under
`projects/instruqt/`. It can point at this repository as course content and bind
operator-built images, but it is not a dependency of the Demo Cloud deployment.
Add it only when there is a concrete hands-on course to publish.

## Registry references

- [Demo Cloud Registry onboarding](https://github.com/temporal-sa/tmprl-demo-cloud-registry#supported-onboarding-path)
- [`projects/README.md`](https://github.com/temporal-sa/tmprl-demo-cloud-registry/blob/main/projects/README.md)
- [Canonical AI demo declaration](https://github.com/temporal-sa/tmprl-demo-cloud-registry/blob/main/projects/demo/canonical-ai-demo.yaml)
- [Multi-image demo declaration](https://github.com/temporal-sa/tmprl-demo-cloud-registry/blob/main/projects/demo/dejavu-tacos.yaml)
- [`DemoProject` JSON schema](https://github.com/temporal-sa/tmprl-demo-cloud-registry/blob/main/schemas/project.schema.json)
