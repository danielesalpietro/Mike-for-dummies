# Mike — Enterprise AI Platform

**Mike** è un assistente AI open-source per la gestione documentale, esteso in questa versione a una piattaforma enterprise completa. Ogni componente gira in Docker: nessuna dipendenza da installare sulla macchina host.

---

## Architettura

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx (porta 80)                         │
│              Reverse proxy unificato per tutti i servizi        │
└────────┬────────┬────────┬──────────┬──────────┬───────────────┘
         │        │        │          │          │
    ┌────▼───┐ ┌──▼──┐ ┌───▼───┐ ┌───▼───┐ ┌────▼─────┐
    │ Mike   │ │Open │ │Airflow│ │Supers.│ │Keycloak  │
    │Frontend│ │WebUI│ │  :80  │ │ :8088 │ │  SSO     │
    │  :3000 │ │:3002│ │       │ │       │ │  :8443   │
    └────┬───┘ └──┬──┘ └───┬───┘ └───────┘ └──────────┘
         │        │        │
    ┌────▼───┐ ┌──▼────┐ ┌─▼──────────┐
    │ Mike   │ │Ollama │ │Spark Master│
    │Backend │ │:11434 │ │  + Worker  │
    │  :3001 │ └───────┘ └─┬──────────┘
    └────┬───┘             │
         │              ┌──▼───┐
    ┌────▼───────────────────────────────────────────┐
    │              Livello Dati & AI                  │
    │                                                 │
    │  PostgreSQL  Redis   MinIO   Qdrant   MLflow    │
    │    :5432     :6379   :9000   :6333    :5000     │
    │                                                 │
    │        RAG Service      Mem0 Service            │
    │           :8001            :8002                │
    └─────────────────────────────────────────────────┘
```

### I cinque livelli

| Livello | Componenti | Scopo |
|---|---|---|
| **Applicazione** | Mike Frontend + Backend | UI documentale, chat AI, workflow |
| **AI** | Qdrant · RAG · Mem0 · MLflow · Ollama · Open WebUI | Retrieval, memoria utente, LLM locale, governance modelli |
| **Data Engineering** | Airflow · Spark · Livy | Orchestrazione pipeline, ETL su larga scala, job Spark via REST |
| **BI** | Apache Superset | Dashboard, Text-to-SQL, analisi quantitativa |
| **Sicurezza** | Keycloak SSO · Nginx | Autenticazione centralizzata, reverse proxy unificato |

---

## Quick Start

### Requisiti

- Docker Engine 24+ e Docker Compose v2
- Python 3.8+ (solo per il wizard di setup)
- 8 GB RAM (16 GB consigliati per il profilo `full`)

### 1. Configura

```bash
python setup.py
```

Il wizard crea `backend/.env`, `frontend/.env.local` e `.env` (root). Gestisce:
- Credenziali Supabase (auth + DB hosted per Mike)
- Scelta storage: **MinIO locale** (default, nessun account) o **Cloudflare R2**
- Chiavi LLM (Anthropic, Gemini, OpenRouter)
- Secret auto-generati per Redis, Superset, Airflow, Keycloak, Open WebUI

### 2. Avvia

```bash
make up          # solo Mike (frontend + backend + postgres + redis + minio)
make up-ai       # + stack AI (Qdrant · RAG · Mem0 · MLflow · Ollama · Open WebUI)
make up-data     # + data engineering (Airflow · Spark · Livy)
make up-bi       # + BI (Superset)
make up-full     # tutto insieme
```

Dopo `make up-ai`, scarica un modello LLM in Ollama:

```bash
make ollama-pull          # scarica llama3.2 (default)
# oppure manualmente:
docker exec mike_ollama ollama pull mistral
```

### 3. Accedi

| Servizio | URL | Credenziali default |
|---|---|---|
| **Mike** | http://localhost:3000 | via Supabase |
| **Open WebUI** (chat LLM) | http://localhost:3002 | primo signup |
| **Airflow** | http://localhost:8080 | admin / admin |
| **Superset** | http://localhost:8088 | admin / admin |
| **MLflow** | http://localhost:5000 | — |
| **Keycloak SSO** | http://localhost:8443 | admin / admin |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin_secret |
| **Spark UI** | http://localhost:8090 | — |
| **Qdrant UI** | http://localhost:6333/dashboard | — |

Tutti i servizi sono raggiungibili anche attraverso Nginx su `http://localhost`.

---

## Come funziona la catena RAG

```
Utente → Mike UI
           │
           ▼
    RAG Service (:8001)
           │  cerca in
           ▼
        Qdrant (:6333)  ←── Airflow DAG indicizza i documenti di Mike
           │
           │  restituisce chunk rilevanti
           ▼
     Mem0 Service (:8002)  ←── aggiunge preferenze/storico dell'utente
           │
           ▼
        LLM (Ollama / Anthropic / Gemini)
           │
           ▼
    Risposta personalizzata, ancorata ai dati aziendali
```

1. **Airflow** schedula il DAG `document_ingestion` (ogni ora): legge i documenti dal DB, li spezza in chunk e li inserisce in **Qdrant** tramite il **RAG Service**.
2. Quando l'utente fa una domanda, il **RAG Service** converte la query in un vettore (sentence-transformers) e recupera i passage più simili.
3. **Mem0** aggiunge al contesto le preferenze persistenti dell'utente (es. "preferisco i report in formato tabellare").
4. Il bundle — documenti recuperati + memoria + domanda — viene inviato all'LLM.
5. **MLflow** traccia le versioni dei modelli di embedding e degli LLM usati.

---

## Struttura del repository

```
Mike-for-dummies/
├── docker-compose.yml          # definizione di tutti i servizi (con profili)
├── .env.example                # template variabili d'ambiente
├── Makefile                    # comandi di avvio/stop
├── setup.py                    # wizard di configurazione interattivo
│
├── backend/                    # Express/TypeScript API
│   └── Dockerfile              # multi-stage: development · builder · production
│
├── frontend/                   # Next.js 16 UI
│   └── Dockerfile              # multi-stage: development · builder · production
│
├── infra/
│   └── postgres/
│       └── init-multiple-dbs.sh  # crea airflow/mlflow/superset/keycloak al primo avvio
│
├── nginx/
│   └── nginx.conf              # reverse proxy (+ blocco HTTPS commentato)
│
└── services/
    ├── rag/                    # FastAPI: embed → upsert Qdrant · semantic search
    │   ├── main.py
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── mem0/                   # FastAPI: memoria personalizzata per utente (mem0ai)
    │   ├── main.py
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── livy/                   # Apache Livy 0.8 — REST API per Spark
    │   ├── Dockerfile
    │   └── livy.conf
    ├── airflow/
    │   └── dags/
    │       └── document_ingestion.py  # DAG: chunk + embed + ingest in Qdrant
    └── superset/
        └── superset_config.py  # Redis cache, RBAC, embedded charts
```

---

## Profili Docker Compose

I servizi sono organizzati in profili attivabili selettivamente:

```bash
docker compose --profile ai up -d
docker compose --profile data up -d
docker compose --profile bi up -d
docker compose --profile security up -d

# combinazioni
docker compose --profile ai --profile bi up -d
```

I servizi **senza profilo** (Mike frontend/backend, PostgreSQL, Redis, MinIO) partono sempre.

---

## Configurazione avanzata

### GPU (Ollama)

Decommentare il blocco `deploy` nel servizio `ollama` di `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

### HTTPS (Nginx)

1. Inserire `cert.pem` e `key.pem` in `nginx/ssl/`
2. Decommentare il blocco `server { listen 443 ssl ... }` in `nginx/nginx.conf`
3. `docker compose --profile security restart nginx`

### Modello di embedding

Il modello `sentence-transformers/all-MiniLM-L6-v2` è scaricato nella build Docker. Per cambiarlo:

```bash
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2 docker compose --profile ai up -d
```

### Porte personalizzate

Tutte le porte sono configurabili nel file `.env` (vedere `.env.example`).

---

## Requisiti esterni

Mike usa Supabase per autenticazione e database applicativo. Questi servizi **non** vengono sostituiti da questa distribuzione:

- **Supabase** — Auth + PostgreSQL hosted per Mike (gratuito fino a 500 MB)
- **Chiave LLM** — Anthropic, Gemini, o OpenRouter (oppure solo Ollama locale)

Tutti gli altri componenti (PostgreSQL per i servizi enterprise, Redis, MinIO, Qdrant, ecc.) sono inclusi e girano in locale.

---

## Comandi utili

```bash
make help           # mostra tutti i comandi disponibili
make ps             # stato dei container
make logs           # tail log in tempo reale
make down           # ferma i servizi core
make down-full      # ferma tutto
make clean          # rimuove container e immagini dangling
make clean-volumes  # ATTENZIONE: elimina tutti i dati persistenti
```

---

## Licenza

AGPL-3.0-only. Vedere `LICENSE`.
