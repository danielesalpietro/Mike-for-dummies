# Mike for Dummies

**Mike Legal Assistant — Private AI, 100% Open Source.**
A self-hosted AI legal assistant that runs entirely on your own infrastructure. No data leaves your network.

Two deployment modes:
- **Docker** — quick setup on any machine
- **LXD on MicroCloud** — production deployment on private Ubuntu infrastructure

---

## Repository Structure

| Path | Description |
|---|---|
| `frontend/` | Next.js application |
| `backend/` | Express API, Supabase integration, document processing |
| `backend/migrations/` | Supabase SQL schema for fresh databases |
| `docker-compose.yml` | Docker stack for local development |
| `setup.py` | Interactive wizard to generate `.env` files |
| `lxd/` | LXD profiles and launch scripts for MicroCloud deployment |

---

## Mode 1 — Docker (local development)

### Requirements
- Docker and Docker Compose
- Credentials for external services (see below)

### Quick Start

```bash
# 1. Configure environment files
python setup.py

# 2. Start the stack
docker compose up --build

# 3. Open your browser
# http://localhost:3000
```

---

## Mode 2 — LXD on MicroCloud (private infrastructure)

This mode replaces Docker entirely. Each service runs in a native Ubuntu LXD container — no Docker installed on the host. Designed for private server deployment with MicroCloud.

### Tested Stack

```
Windows 10 Pro
  └── VMware Workstation
        └── Ubuntu 24.04 LTS (VM)
              └── MicroCloud + LXD
                    ├── Container: mike-backend  (Node.js + Express, port 3001)
                    └── Container: mike-frontend (Next.js, port 3000)
```

### Requirements

- Ubuntu 22.04+ with LXD initialized (`lxd init`)
- MicroCloud configured (fan network `lxdfan0`, ZFS storage pool `local`)
- Node.js **not required** on the host (installed inside containers by cloud-init)
- Repository cloned on a local filesystem (not NFS/FUSE)

### Configuration

**1. Set up environment files**

```bash
python setup.py
# or manually:
nano backend/.env
nano frontend/.env.local
```

Required in `backend/.env`:
```
FRONTEND_URL=http://<HOST-IP>:3000   # Ubuntu host IP, e.g. 192.168.1.10
```

Required in `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...
NEXT_PUBLIC_API_BASE_URL=http://<HOST-IP>:3001
```

> **Important:** always use the real host IP (e.g. `192.168.206.140`), never `localhost` — the browser needs to reach both services over the network.

**2. Adapt LXD profiles to your environment** (first run only)

Check available network and storage:
```bash
lxc network list   # find the LXD-managed bridge network
lxc storage list   # find the storage pool
```

Update `lxd/profiles/common.yaml` with your values:
```yaml
devices:
  eth0:
    network: lxdfan0   # replace with your network name
    type: nic
  root:
    pool: local        # replace with your storage pool name
    type: disk
```

### Launch

```bash
cd lxd/
./launch.sh            # start backend + frontend
./launch.sh backend    # start backend only
./launch.sh frontend   # start frontend only
```

The script automatically:
1. Creates LXD profiles (`mike-common`, `mike-backend`, `mike-frontend`)
2. Launches two `ubuntu:22.04` containers
3. cloud-init installs Node.js 20, build tools, and LibreOffice (backend only)
4. Mounts source code into containers via disk device (`shift=true` for permissions)
5. Runs `npm install` inside each container
6. Reads `.env` files and injects environment variables
7. Starts dev servers as systemd services

### Access

```
http://<HOST-IP>:3000   ← Frontend (Next.js)
http://<HOST-IP>:3001   ← Backend  (Express API)
```

### Daily Operations

```bash
# Container status
lxc list mike-

# Live logs
lxc exec mike-backend  -- journalctl -fu mike-backend.service
lxc exec mike-frontend -- journalctl -fu mike-frontend.service

# Shell into a container
lxc exec mike-backend  -- bash
lxc exec mike-frontend -- bash

# Update code (bind-mounts reflect changes immediately)
git pull
# tsx watch / Next.js detect file changes automatically

# Stop everything
./teardown.sh
```

### Docker → LXD Mapping

| `docker-compose.yml` | LXD equivalent |
|---|---|
| `FROM node:20-bullseye-slim` | `lxc launch ubuntu:22.04` + NodeSource 20 via cloud-init |
| `RUN apt-get install ...` | cloud-init `packages` + `runcmd` |
| `volumes: ./backend:/app` | `disk` device with `shift=true` |
| `ports: "3001:3001"` | `proxy` device |
| `env_file:` | `lxc config set environment.*` |
| `CMD ["npm", "run", "dev"]` | systemd unit `mike-backend.service` |
| `depends_on:` | sequential order in `launch.sh` |

---

## Required External Services

Both deployment modes require:

| Service | Purpose |
|---|---|
| **Supabase** | Authentication and database |
| **Cloudflare R2** | S3-compatible document storage |
| **Anthropic / Gemini** | LLM API for AI responses |

> **Roadmap:** local LLM integration via Ollama for fully air-gapped operation with no external API dependencies.

---

## Why LXD instead of Docker?

- **Real isolation:** each service is a lightweight Ubuntu system, not just a namespaced process
- **Native systemd:** manage services with `systemctl` like any Linux process
- **MicroCloud integration:** distributed Ceph storage, OVN networking, multi-node clustering
- **No Docker daemon:** reduced attack surface, no dependency on the Docker socket
- **Private AI:** all code, data, and models stay within your own infrastructure

---

## Credits & License

Based on the original [Mike](https://github.com/Brudanstudio/mike) project.

LXD deployment & setup wizard: [danielesalpietro](https://github.com/danielesalpietro)

License: **AGPL-3.0-only** — see `LICENSE`.

# ITALIAN 

# Mike for Dummies

**Mike Legal Assistant — Private AI, 100% Open Source.**
Assistente legale AI che gira interamente sulla tua infrastruttura, senza dati che escono dalla tua rete.

Due modalità di deployment:
- **Docker** — per sviluppo rapido su qualsiasi macchina
- **LXD su MicroCloud** — per produzione su infrastruttura privata Ubuntu

---

## Contenuto del repository

| Cartella/File | Descrizione |
|---|---|
| `frontend/` | Applicazione Next.js |
| `backend/` | API Express, integrazione Supabase, elaborazione documenti |
| `backend/migrations/` | Schema SQL Supabase per nuovi database |
| `docker-compose.yml` | Stack Docker per sviluppo locale |
| `setup.py` | Wizard interattivo per la configurazione dei file `.env` |
| `lxd/` | Profili e script per deployment su LXD/MicroCloud |

---

## Modalità 1 — Docker (sviluppo locale)

### Requisiti
- Docker e Docker Compose
- Credenziali per i servizi esterni (vedi sotto)

### Avvio

```bash
# 1. Configura i file .env
python setup.py

# 2. Avvia lo stack
docker compose up --build

# 3. Apri il browser
# http://localhost:3000
```

---

## Modalità 2 — LXD su MicroCloud (infrastruttura privata)

Questa modalità sostituisce completamente Docker: ogni servizio gira in un container LXD nativo Ubuntu, senza Docker installato sull'host. Ideale per deployment su server privato con MicroCloud.

### Stack hardware/software testato

```
Windows 10 Pro
  └── VMware Workstation
        └── Ubuntu 24.04 LTS (VM)
              └── MicroCloud + LXD
                    ├── Container: mike-backend  (Node.js + Express, porta 3001)
                    └── Container: mike-frontend (Next.js, porta 3000)
```

### Requisiti

- Ubuntu 22.04+ con LXD inizializzato (`lxd init`)
- MicroCloud configurato (rete fan `lxdfan0`, storage pool `local` su ZFS)
- Node.js **non** necessario sull'host (installato nel container da cloud-init)
- Repository clonato su filesystem locale (non NFS/FUSE)

### Configurazione prima dell'avvio

**1. Configura i file `.env`**

```bash
python setup.py
# oppure manualmente:
nano backend/.env
nano frontend/.env.local
```

Variabili necessarie nel `backend/.env`:
```
FRONTEND_URL=http://<IP-HOST>:3000   # IP dell'host Ubuntu, es. 192.168.1.10
```

Variabili necessarie nel `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=sb_publishable_...
SUPABASE_SECRET_KEY=sb_secret_...
NEXT_PUBLIC_API_BASE_URL=http://<IP-HOST>:3001
```

> **Importante:** usa sempre l'IP reale dell'host (es. `192.168.206.140`), mai `localhost`, perché il browser degli utenti deve raggiungere i servizi dalla rete.

**2. Adatta i profili LXD al tuo ambiente** (solo prima installazione)

Verifica rete e storage disponibili:
```bash
lxc network list   # cerca la rete bridge gestita da LXD
lxc storage list   # cerca il pool di storage
```

Aggiorna `lxd/profiles/common.yaml` con i valori trovati:
```yaml
devices:
  eth0:
    network: lxdfan0   # sostituisci con il nome della tua rete
    type: nic
  root:
    pool: local        # sostituisci con il nome del tuo pool
    type: disk
```

### Avvio

```bash
cd lxd/
./launch.sh            # avvia backend + frontend
./launch.sh backend    # avvia solo il backend
./launch.sh frontend   # avvia solo il frontend
```

Lo script esegue in automatico:
1. Crea i profili LXD (`mike-common`, `mike-backend`, `mike-frontend`)
2. Lancia due container `ubuntu:22.04`
3. cloud-init installa Node.js 20, dipendenze di sistema e LibreOffice (backend)
4. Monta il codice sorgente nei container via disk device (`shift=true` per i permessi)
5. Esegue `npm install` dentro ogni container
6. Legge i file `.env` e inietta le variabili d'ambiente
7. Avvia i dev server come servizi systemd

### Accesso

```
http://<IP-HOST>:3000   ← Frontend (Next.js)
http://<IP-HOST>:3001   ← Backend  (Express API)
```

### Gestione quotidiana

```bash
# Stato container
lxc list mike-

# Log in tempo reale
lxc exec mike-backend  -- journalctl -fu mike-backend.service
lxc exec mike-frontend -- journalctl -fu mike-frontend.service

# Shell dentro un container
lxc exec mike-backend  -- bash
lxc exec mike-frontend -- bash

# Aggiornare il codice (i bind-mount riflettono subito le modifiche)
git pull
# i watcher tsx/Next.js rilevano i cambiamenti automaticamente

# Spegnere tutto
./teardown.sh
```

### Mappatura Docker → LXD

| `docker-compose.yml` | LXD |
|---|---|
| `FROM node:20-bullseye-slim` | `lxc launch ubuntu:22.04` + NodeSource 20 via cloud-init |
| `RUN apt-get install ...` | cloud-init `packages` + `runcmd` |
| `volumes: ./backend:/app` | `disk` device con `shift=true` |
| `ports: "3001:3001"` | `proxy` device |
| `env_file:` | `lxc config set environment.*` |
| `CMD ["npm", "run", "dev"]` | systemd unit `mike-backend.service` |
| `depends_on:` | ordine sequenziale in `launch.sh` |

---

## Servizi esterni richiesti

Entrambe le modalità (Docker e LXD) richiedono:

| Servizio | Uso |
|---|---|
| **Supabase** | Autenticazione e database |
| **Cloudflare R2** | Storage documenti (S3-compatible) |
| **Anthropic / Gemini** | LLM per le risposte AI |

> **Roadmap:** integrazione con LLM locali (Ollama) per operatività 100% air-gapped, senza dipendenze da API esterne.

---

## Perché LXD invece di Docker?

- **Isolamento reale:** ogni servizio è una VM leggera Ubuntu, non un processo containerizzato
- **Systemd nativo:** i servizi si gestiscono con `systemctl`, come qualsiasi processo Linux
- **Integrazione MicroCloud:** storage Ceph distribuito, rete OVN, clustering multi-nodo
- **Nessun Docker daemon:** superficie d'attacco ridotta, nessuna dipendenza da Docker socket
- **Private AI:** tutto il codice, i dati e i modelli rimangono nella tua infrastruttura

---

## Crediti e Licenza

Basato sul progetto originale [Mike](https://github.com/Brudanstudio/mike).

LXD deployment & wizard: [danielesalpietro](https://github.com/danielesalpietro)

Licenza: **AGPL-3.0-only** — vedi `LICENSE`.

