# Mike — Self-Hosted Full Stack

> A fully containerized, self-hosted deployment of [Mike Legal Assistant](https://github.com/willchen96/mike) — no Supabase cloud account, no Cloudflare R2, no external services required.
>
> Built and tested on **Windows 11 + Docker Desktop (Intel/AMD)**. Should work on macOS and Linux too.

---

## What this branch adds

The upstream Mike repo expects a hosted Supabase project and Cloudflare R2 bucket. This branch wires up the full self-hosted equivalent inside Docker Compose, and extends Mike with persistent AI memory via [mem0](https://github.com/mem-0/mem0):

| Upstream (cloud) | This branch (local Docker) |
|---|---|
| Supabase Auth (hosted) | GoTrue (self-hosted) |
| Supabase PostgREST (hosted) | PostgREST + PostgreSQL 15 |
| Supabase DB (hosted) | PostgreSQL 15-alpine |
| Cloudflare R2 | MinIO (S3-compatible) |
| *(no memory)* | mem0 + Qdrant (persistent AI memory) |

---

## Architecture

```
Browser (localhost:3000)
    │
    ├─► mike-frontend  :3000   Next.js 16
    │
    └─► mike-backend   :3001   Express + TypeScript
            │
            ├─► supabase-api   :8000   nginx gateway
            │       ├─► /auth/v1/*  → supabase-auth  :9999  (GoTrue)
            │       └─► /rest/v1/*  → supabase-rest  :3000  (PostgREST)
            │                               └─► supabase-db  :5432  (PostgreSQL)
            │
            ├─► minio          :9000   S3-compatible storage
            │       └─► minio console  :9001
            │
            └─► mem0-service   :8100   Memory microservice (FastAPI)
                    └─► qdrant :6333   Vector store
```

**Startup order:**
1. `supabase-db` starts → healthcheck passes
2. `qdrant` starts → healthcheck passes
3. `supabase-auth` + `supabase-rest` + `minio` start
4. `supabase-api` (nginx) and `mem0-service` start
5. `db-migrate` runs the one-shot schema (waits 20 s for GoTrue migrations, then sends `NOTIFY pgrst` to refresh PostgREST schema cache)
6. `minio-setup` creates the storage bucket
7. `mike-backend` + `mike-frontend` start

> `mem0-service` is a non-fatal dependency: if it fails to start (e.g. missing API key), Mike continues to work normally without memory.

---

## AI Memory (mem0)

Mike remembers facts across conversations using [mem0ai](https://github.com/mem-0/mem0), a library that extracts and indexes key information from chat exchanges.

### How it works

1. **Before each LLM call** — the backend searches for memories relevant to the current query and injects them into the system prompt.
2. **After each LLM response** — the exchange is sent to `mem0-service`, which uses Claude to extract memorable facts and stores them as vectors in Qdrant.

### Memory scopes

Memory is scoped to avoid cross-contamination between unrelated contexts:

| Context | Scope | Behaviour |
|---|---|---|
| Standalone chat (`/assistant`) | Per chat session | Each chat has its own isolated memory. Starting a new chat starts fresh. |
| Project chat (`/projects/…`) | Per project | All chats within the same project share memory. Information from one session is available in all subsequent sessions of that project. |

This means: if you tell Mike your name and role in a project chat, it will remember it across all future sessions in that project. A separate standalone chat will not have access to that information.

### API keys used by mem0

mem0 uses two external APIs — both keys you already have in `.env`:

| Key | Used for | Required |
|---|---|---|
| `GEMINI_API_KEY` | Generating text embeddings (`gemini-embedding-001`) | Yes |
| `ANTHROPIC_API_KEY` | Extracting and reasoning about memories (Claude Haiku) | Yes |

> If your Anthropic credit balance runs out, `memories/add` will fail silently — Mike keeps working but stops accumulating new memories. The service status indicator in the UI will show "LLM (Anthropic)" as red with a message prompting you to top up at [console.anthropic.com](https://console.anthropic.com).

---

## Service status indicator

A status dot appears on your avatar in the sidebar (bottom-left). Click it to see the health of all backend services in real time:

| Service | What is checked |
|---|---|
| Database | PostgREST query against `user_profiles` |
| Storage | HTTP HEAD against the MinIO bucket |
| Memory (Mem0) | `GET /health` on the mem0 microservice |
| LLM (Anthropic) | Minimal API call (cached 5 min to avoid unnecessary spend) |

Colours: 🟢 online · 🟡 starting · 🔴 unavailable. When Anthropic credits are exhausted the LLM row shows a specific message with a link to the billing page.

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2 on Linux)
- A **Gemini** API key (`GEMINI_API_KEY`) — for embeddings and as a fallback LLM
- An **Anthropic** API key (`ANTHROPIC_API_KEY`) — for chat and memory reasoning
- ~5 GB free disk space (images + node_modules volumes + Qdrant data)

No Node.js, no Python, no LibreOffice on the host — everything runs inside containers.

---

## Quick start

```bash
# 1. Clone
git clone -b feat/mem0-integration \
  https://github.com/danielesalpietro/Mike-for-dummies.git
cd Mike-for-dummies

# 2. Create your .env
cp .env.docker .env
```

Open `.env` and fill in at minimum:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...          # required for chat + memory reasoning
GEMINI_API_KEY=AIza...                # required for embeddings
DOWNLOAD_SIGNING_SECRET=<random 32+ chars>  # openssl rand -hex 32
```

Everything else (JWT keys, MinIO credentials, ports) is pre-configured for local use.

```bash
# 3. Build and start
docker compose up --build
```

First run takes a few minutes (downloads images, installs npm packages inside containers).

```bash
# 4. Open the app
http://localhost:3000
```

---

## Services and ports

| Service | Port | Description |
|---|---|---|
| mike-frontend | `3000` | Next.js web UI |
| mike-backend | `3001` | Express REST API |
| supabase-api (nginx) | `8000` | Supabase API gateway |
| minio API | `9000` | S3-compatible storage endpoint |
| minio console | `9001` | MinIO web UI (`minioadmin` / `minioadmin`) |

Internal services (not exposed to host): `supabase-db` (5432), `supabase-auth` (9999), `supabase-rest` (3000), `mem0-service` (8100), `qdrant` (6333).

---

## Environment variables

All variables live in `.env` (copy from `.env.docker`). Defaults are safe for local development — **never use them in production**.

### PostgreSQL

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `postgres` | Password for the `postgres` superuser |

### Supabase JWT

> ⚠️ Do not change `JWT_SECRET` without also regenerating `ANON_KEY` and `SERVICE_ROLE_KEY`. All three must be consistent.

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | `super-secret-jwt-token-with-at-least-32-characters-long` | HMAC secret for signing JWTs |
| `ANON_KEY` | Pre-generated (expires 2033) | Public key sent by the frontend |
| `SERVICE_ROLE_KEY` | Pre-generated (expires 2033) | Backend service key (bypasses RLS) |

To regenerate keys with a custom secret:
```bash
node -e "
const crypto = require('crypto');
const secret = 'your-custom-secret-at-least-32-chars';
const mk = p => { const h = Buffer.from(JSON.stringify({alg:'HS256',typ:'JWT'})).toString('base64url'); const pl = Buffer.from(JSON.stringify(p)).toString('base64url'); return h+'.'+pl+'.'+crypto.createHmac('sha256',secret).update(h+'.'+pl).digest('base64url'); };
console.log('ANON_KEY='+mk({iss:'supabase-demo',role:'anon',exp:1983812996}));
console.log('SERVICE_ROLE_KEY='+mk({iss:'supabase-demo',role:'service_role',exp:1983812996}));
"
```

### MinIO / Storage

| Variable | Default | Description |
|---|---|---|
| `MINIO_ROOT_USER` | `minioadmin` | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO admin password |
| `R2_BUCKET_NAME` | `mike` | Bucket name for document storage |

### Backend / LLM

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic Claude API key |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key |
| `DOWNLOAD_SIGNING_SECRET` | *(empty — **required**)* | Random secret for signed download URLs. Generate with `openssl rand -hex 32` |
| `PORT` | `3001` | Backend port |
| `FRONTEND_URL` | `http://localhost:3000` | Allowed CORS origin |

### mem0 (optional overrides)

| Variable | Default | Description |
|---|---|---|
| `MEM0_LLM_MODEL` | `claude-haiku-4-5-20251001` | Anthropic model used by mem0 for memory extraction |
| `MEM0_EMBEDDER_MODEL` | `gemini-embedding-001` | Gemini model used for vector embeddings |

### Ports (override if there are conflicts)

| Variable | Default |
|---|---|
| `SUPABASE_PORT` | `8000` |
| `MINIO_API_PORT` | `9000` |
| `MINIO_CONSOLE_PORT` | `9001` |

---

## Updating

```bash
git pull
docker compose up --build   # rebuilds only changed images
```

If you see unexpected errors after updating, a clean rebuild fixes most issues:

```bash
docker compose down -v      # removes containers AND named volumes (node_modules)
docker compose up --build
```

> **Note:** the PostgreSQL data directory (`supabase/postgres/data/`) and the Qdrant data volume (`qdrant-data`) are **not** deleted by `down -v`. Your database records and memories persist across rebuilds.

---

## Troubleshooting

### Frontend or backend crash-loops silently
Named volumes (`frontend-node-modules`, `backend-node-modules`) may be stale. Run `docker compose down -v && docker compose up --build`.

### `JWSInvalidSignature` / 401 from PostgREST
`JWT_SECRET`, `ANON_KEY`, and `SERVICE_ROLE_KEY` are inconsistent. See the key regeneration snippet above and restart with `docker compose up -d --force-recreate supabase-rest supabase-auth mike-backend mike-frontend`.

### `ENOTFOUND mike.minio` on document upload
S3 path-style is required for MinIO. Already fixed in this branch (`forcePathStyle: true` in `backend/src/lib/storage.ts`). If you see this, make sure you are on this branch and have rebuilt the backend image.

### `Failed to fetch` on login / signup
Check that `supabase-api` is running: `docker compose ps`. Nginx must be able to reach `supabase-auth:9999`. Wait ~30 seconds on first startup for GoTrue migrations to complete.

### Profile settings (display name etc.) return 404
This happens when PostgREST loads its schema cache before the migration runs. The migration now sends `NOTIFY pgrst` at the end to trigger a schema reload automatically. If you still see this, run `docker compose restart supabase-rest`.

### mem0 `memories/add` returns 500
Check `docker compose logs mem0-service`. Common causes:
- **Anthropic credit balance too low** — top up at [console.anthropic.com](https://console.anthropic.com). Visible as a red "LLM (Anthropic)" entry in the status popover.
- **Qdrant collection dimension mismatch** — happens if you previously ran mem0 with a different embedding model. Fix: `docker compose exec mem0-service python -c "from qdrant_client import QdrantClient; c = QdrantClient(host='qdrant', port=6333); c.delete_collection('mike_memories'); c.delete_collection('mem0migrations')"` then restart mem0-service.

### Port conflict
Change the relevant `*_PORT` variable in `.env` and run `docker compose up -d`.

---

## Database schema

The one-shot migration (`backend/migrations/000_one_shot_schema.sql`) creates these tables in the `public` schema on first startup:

- `user_profiles` — display name, org, tier, credit tracking, per-user API keys
- `projects` + `project_subfolders` — project containers and folder hierarchy
- `documents` + `document_versions` + `document_edits` — files with version history and tracked changes
- `workflows` + `hidden_workflows` + `workflow_shares` — custom AI workflows
- `chats` + `chat_messages` — assistant chat sessions
- `tabular_reviews` + `tabular_cells` + `tabular_review_chats` + `tabular_review_chat_messages` — structured tabular review features

Row-level security (RLS) is enabled on all user-facing tables.

---

## Credits

**Original project:** [Mike Legal Assistant](https://github.com/willchen96/mike) by [@willchen96](https://github.com/willchen96) and contributors — all application logic, frontend, and backend belong to the original authors.

**This branch** (self-hosted Docker Compose setup + mem0 integration): [@danielesalpietro](https://github.com/danielesalpietro)

---

## License

AGPL-3.0-only. See [`LICENSE`](LICENSE).
