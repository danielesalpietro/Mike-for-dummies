# Mike — Self-Hosted Full Stack

> A fully containerized, self-hosted deployment of [Mike Legal Assistant](https://github.com/willchen96/mike) — no Supabase cloud account, no Cloudflare R2, no external services required.
>
> Built and tested on **Windows 11 + Docker Desktop (Intel/AMD)**. Should work on macOS and Linux too.

---

## What this branch adds

The upstream Mike repo expects a hosted Supabase project and Cloudflare R2 bucket. This branch wires up the full self-hosted equivalent inside Docker Compose:

| Upstream (cloud) | This branch (local Docker) |
|---|---|
| Supabase Auth (hosted) | GoTrue (self-hosted) |
| Supabase PostgREST (hosted) | PostgREST + PostgreSQL 15 |
| Supabase DB (hosted) | PostgreSQL 15-alpine |
| Cloudflare R2 | MinIO (S3-compatible) |

Everything else (frontend, backend, document processing, LLM integration) is unchanged from upstream.

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
            └─► minio          :9000   S3-compatible storage
                    └─► minio console  :9001
```

**Startup order:**
1. `supabase-db` starts → healthcheck passes
2. `supabase-auth` + `supabase-rest` start (depend on db)
3. `supabase-api` (nginx) starts (depends on auth + rest)
4. `db-migrate` runs the one-shot schema (waits 20 s for GoTrue to finish its own migrations)
5. `minio` starts → `minio-setup` creates the bucket
6. `mike-backend` + `mike-frontend` start

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2 on Linux)
- An **Anthropic** and/or **Gemini** API key (for LLM features)
- ~4 GB free disk space (images + node_modules volumes)

No Node.js, no Python, no LibreOffice on the host — everything runs inside containers.

---

## Quick start

```bash
# 1. Clone
git clone -b Mike-self-hosted-full-stack \
  https://github.com/danielesalpietro/Mike-for-dummies.git
cd Mike-for-dummies

# 2. Create your .env
cp .env.docker .env
```

Open `.env` and fill in at minimum:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...          # at least one LLM key required
GEMINI_API_KEY=AIza...                # optional second provider
DOWNLOAD_SIGNING_SECRET=<random 32+  chars>  # openssl rand -hex 32
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

Internal services (not exposed to host): `supabase-db` (5432), `supabase-auth` (9999), `supabase-rest` (3000).

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

### Backend

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic Claude API key |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key |
| `DOWNLOAD_SIGNING_SECRET` | *(empty — **required**)* | Random secret for signed download URLs. Generate with `openssl rand -hex 32` |
| `PORT` | `3001` | Backend port |
| `FRONTEND_URL` | `http://localhost:3000` | Allowed CORS origin |

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

> **Note:** the PostgreSQL data directory (`supabase/postgres/data/`) is a bind-mount and is NOT deleted by `down -v`. Your data persists across rebuilds.

---

## Troubleshooting

### Frontend or backend crash-loops silently
Named volumes (`frontend-node-modules`, `backend-node-modules`) may be stale. Run `docker compose down -v && docker compose up --build`.

### `JWSInvalidSignature` / 401 from PostgREST
`JWT_SECRET`, `ANON_KEY`, and `SERVICE_ROLE_KEY` are inconsistent. See the key regeneration snippet above and restart with `docker compose up -d --force-recreate supabase-rest supabase-auth mike-backend mike-frontend`.

### `ENOTFOUND mike.minio` on document upload
S3 path-style is required for MinIO. Already fixed in this branch (`forcePathStyle: true` in `backend/src/lib/storage.ts`). If you see this, make sure you are on this branch and have rebuilt the backend image.

### `Failed to fetch` on login / signup
Check that `supabase-api` is running and healthy: `docker compose ps`. Nginx must be able to reach `supabase-auth:9999`.

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

**This branch** (self-hosted Docker Compose setup): [@danielesalpietro](https://github.com/danielesalpietro)

---

## License

AGPL-3.0-only. See [`LICENSE`](LICENSE).
