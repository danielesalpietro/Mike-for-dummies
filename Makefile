.PHONY: help up up-ai up-data up-bi up-security up-full \
        down down-full logs ps build pull \
        ollama-pull mlflow-init superset-init \
        clean clean-volumes

# Default target
help:
	@echo ""
	@echo "  Mike Enterprise AI Platform"
	@echo "  ─────────────────────────────────────────────────────────"
	@echo "  make setup          Interactive setup wizard (configure .env files)"
	@echo ""
	@echo "  Startup commands:"
	@echo "  make up             Core app only (frontend + backend + postgres + redis + minio)"
	@echo "  make up-ai          Core + AI stack (Qdrant, RAG, Mem0, MLflow, Ollama, Open WebUI)"
	@echo "  make up-data        Core + Data engineering (Airflow, Spark, Livy)"
	@echo "  make up-bi          Core + BI (Superset)"
	@echo "  make up-security    Core + Security (Keycloak, Nginx)"
	@echo "  make up-full        Everything"
	@echo ""
	@echo "  Service management:"
	@echo "  make down           Stop core services"
	@echo "  make down-full      Stop all services"
	@echo "  make logs           Tail logs"
	@echo "  make ps             Show running services"
	@echo "  make build          Rebuild all images"
	@echo ""
	@echo "  Utilities:"
	@echo "  make ollama-pull    Pull default Ollama model (llama3.2)"
	@echo "  make clean          Remove containers and dangling images"
	@echo "  make clean-volumes  WARNING: destroys all persistent data"
	@echo ""
	@echo "  Ports:"
	@echo "    3000  Mike frontend"
	@echo "    3001  Mike backend API"
	@echo "    3002  Open WebUI (Ollama chat)"
	@echo "    5000  MLflow tracking"
	@echo "    5432  PostgreSQL"
	@echo "    6333  Qdrant HTTP"
	@echo "    6379  Redis"
	@echo "    8001  RAG service"
	@echo "    8002  Mem0 service"
	@echo "    8080  Airflow"
	@echo "    8088  Superset"
	@echo "    8090  Spark master UI"
	@echo "    8443  Keycloak SSO"
	@echo "    8998  Livy (Spark REST)"
	@echo "    9000  MinIO API"
	@echo "    9001  MinIO console"
	@echo "   11434  Ollama"
	@echo ""

setup:
	python setup.py

# ── Start ─────────────────────────────────────────────────────────────────────

up:
	docker compose up -d

up-ai:
	docker compose --profile ai up -d

up-data:
	docker compose --profile data up -d

up-bi:
	docker compose --profile bi up -d

up-security:
	docker compose --profile security up -d

up-full:
	docker compose \
	  --profile ai \
	  --profile data \
	  --profile bi \
	  --profile security \
	  up -d

# ── Stop ──────────────────────────────────────────────────────────────────────

down:
	docker compose down

down-full:
	docker compose \
	  --profile ai \
	  --profile data \
	  --profile bi \
	  --profile security \
	  down

# ── Utilities ─────────────────────────────────────────────────────────────────

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

build:
	docker compose \
	  --profile ai \
	  --profile data \
	  --profile bi \
	  --profile security \
	  build

pull:
	docker compose \
	  --profile ai \
	  --profile data \
	  --profile bi \
	  --profile security \
	  pull

ollama-pull:
	@echo "Pulling llama3.2 model into Ollama..."
	docker exec mike_ollama ollama pull llama3.2
	@echo "Done. You can pull more models with: docker exec mike_ollama ollama pull <model>"

clean:
	docker compose \
	  --profile ai \
	  --profile data \
	  --profile bi \
	  --profile security \
	  down --remove-orphans
	docker image prune -f

clean-volumes:
	@echo "WARNING: This will delete ALL persistent data (databases, vector store, models)."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker compose \
	  --profile ai \
	  --profile data \
	  --profile bi \
	  --profile security \
	  down -v --remove-orphans
