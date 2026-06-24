"""
Mike Enterprise AI Platform — Interactive Setup Wizard
======================================================
Generates .env files for the backend, frontend, and the root .env
used by Docker Compose for the enterprise services.
"""

import os
import shutil
import secrets
import base64
from datetime import datetime


def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path):
    if os.path.exists(path):
        shutil.copy2(path, f"{path}_{ts()}.bck")
        return True
    return False


def load_env(path):
    data = {}
    if not os.path.exists(path):
        return data
    with open(path) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                data[k.strip()] = v.strip()
    return data


def ask(prompt, current="", secret=False):
    label = "[hidden]" if (secret and current) else current
    if current:
        print(f"   Current: {label}")
        val = input(f"   {prompt} (ENTER to keep): ").strip()
        return val or current
    return input(f"   {prompt}: ").strip()


def gen_secret(n=32):
    return secrets.token_hex(n)


def gen_fernet():
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except ImportError:
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def run():
    print("=" * 60)
    print("  Mike Enterprise AI Platform — Setup Wizard")
    print("=" * 60)

    backend_env_path = "backend/.env"
    frontend_env_path = "frontend/.env.local"
    root_env_path = ".env"

    existing = {}
    for p in (backend_env_path, frontend_env_path, root_env_path):
        existing.update(load_env(p))

    # ── 1. Supabase (Auth + hosted DB for the Mike app) ───────────────────────
    section("STEP 1 · Supabase (Auth & Database for Mike app)")
    print("  Get these from https://supabase.com → Project Settings → API")

    sb_url = ask(
        "Supabase Project URL",
        existing.get("SUPABASE_URL") or existing.get("NEXT_PUBLIC_SUPABASE_URL", ""),
    )
    sb_anon = ask(
        "Supabase Anon Key",
        existing.get("NEXT_PUBLIC_SUPABASE_ANON_KEY") or existing.get("SUPABASE_ANON_KEY", ""),
        secret=True,
    )
    sb_secret = ask(
        "Supabase Service Role Key (Secret)",
        existing.get("SUPABASE_SECRET_KEY") or existing.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        secret=True,
    )

    # ── 2. Storage ────────────────────────────────────────────────────────────
    section("STEP 2 · Storage (Cloudflare R2 or local MinIO)")
    print("  'local' → bundled MinIO container (no account needed).")
    print("  'r2'    → Cloudflare R2.")
    storage_choice = input("  Storage backend [local/r2] (default: local): ").strip().lower()
    if storage_choice != "r2":
        storage_choice = "local"

    if storage_choice == "r2":
        r2_end = ask("R2 Endpoint URL", existing.get("R2_ENDPOINT_URL", ""))
        if ".com/" in r2_end:
            r2_end = r2_end.split(".com/")[0] + ".com"
            print("      → Auto-fixed: bucket name removed from URL.")
        r2_bucket = ask("R2 Bucket Name", existing.get("R2_BUCKET_NAME", "mike"))
        r2_access = ask("R2 Access Key ID", existing.get("R2_ACCESS_KEY_ID", ""), secret=True)
        r2_secret_key = ask("R2 Secret Access Key", existing.get("R2_SECRET_ACCESS_KEY", ""), secret=True)
        minio_user = ""
        minio_pass = ""
    else:
        r2_end = "http://minio:9000"
        r2_bucket = "mike"
        minio_user = ask("MinIO root user", existing.get("MINIO_ROOT_USER", "minioadmin"))
        minio_pass = ask(
            "MinIO root password",
            existing.get("MINIO_ROOT_PASSWORD", gen_secret(12)),
            secret=True,
        )
        r2_access = minio_user
        r2_secret_key = minio_pass

    # ── 3. LLM API keys ───────────────────────────────────────────────────────
    section("STEP 3 · LLM API Keys")
    print("  At least one is needed. Leave others empty to skip.")

    anthropic_key = ask(
        "Anthropic API Key",
        existing.get("ANTHROPIC_API_KEY", ""),
        secret=True,
    )
    gemini_key = ask(
        "Gemini API Key",
        existing.get("GEMINI_API_KEY", ""),
        secret=True,
    )
    openrouter_key = ask(
        "OpenRouter API Key (optional)",
        existing.get("OPENROUTER_API_KEY", ""),
        secret=True,
    )

    # ── 4. Enterprise services ────────────────────────────────────────────────
    section("STEP 4 · Enterprise Services (press ENTER for auto-generated defaults)")

    pg_user = ask("PostgreSQL user", existing.get("POSTGRES_USER", "mike"))
    pg_pass = ask(
        "PostgreSQL password",
        existing.get("POSTGRES_PASSWORD", gen_secret(16)),
        secret=True,
    )
    redis_pass = ask(
        "Redis password",
        existing.get("REDIS_PASSWORD", gen_secret(16)),
        secret=True,
    )

    webui_secret = existing.get("WEBUI_SECRET_KEY") or gen_secret(32)
    superset_secret = existing.get("SUPERSET_SECRET_KEY") or gen_secret(32)
    airflow_fernet = existing.get("AIRFLOW_FERNET_KEY") or gen_fernet()

    keycloak_pass = ask(
        "Keycloak admin password",
        existing.get("KEYCLOAK_ADMIN_PASSWORD", "admin"),
        secret=True,
    )

    # ── 5. Resend (email) ─────────────────────────────────────────────────────
    section("STEP 5 · Resend Email API (optional)")
    resend_key = ask("Resend API Key", existing.get("RESEND_API_KEY", ""), secret=True)

    # ── Write files ───────────────────────────────────────────────────────────
    section("SAVING CONFIGURATION")

    for p in (backend_env_path, frontend_env_path, root_env_path):
        if backup(p):
            print(f"  Backed up: {p}")

    with open(backend_env_path, "w") as f:
        f.write("PORT=3001\n")
        f.write("FRONTEND_URL=http://localhost:3000\n")
        f.write("\n# Supabase\n")
        f.write(f"SUPABASE_URL={sb_url}\n")
        f.write(f"SUPABASE_SECRET_KEY={sb_secret}\n")
        f.write("\n# Storage\n")
        f.write(f"R2_ENDPOINT_URL={r2_end}\n")
        f.write(f"R2_BUCKET_NAME={r2_bucket}\n")
        f.write(f"R2_ACCESS_KEY_ID={r2_access}\n")
        f.write(f"R2_SECRET_ACCESS_KEY={r2_secret_key}\n")
        f.write("R2_REGION=auto\n")
        f.write("\n# AI\n")
        f.write(f"ANTHROPIC_API_KEY={anthropic_key}\n")
        f.write(f"GEMINI_API_KEY={gemini_key}\n")
        f.write(f"OPENROUTER_API_KEY={openrouter_key}\n")
        f.write("\n# Email\n")
        f.write(f"RESEND_API_KEY={resend_key}\n")

    with open(frontend_env_path, "w") as f:
        f.write(f"NEXT_PUBLIC_SUPABASE_URL={sb_url}\n")
        f.write(f"NEXT_PUBLIC_SUPABASE_ANON_KEY={sb_anon}\n")
        f.write("NEXT_PUBLIC_BACKEND_URL=http://localhost:3001\n")

    with open(root_env_path, "w") as f:
        f.write("# Generated by setup.py — do not commit to version control\n\n")
        f.write("# PostgreSQL\n")
        f.write(f"POSTGRES_USER={pg_user}\n")
        f.write(f"POSTGRES_PASSWORD={pg_pass}\n")
        f.write("\n# Redis\n")
        f.write(f"REDIS_PASSWORD={redis_pass}\n")
        if storage_choice == "local":
            f.write("\n# MinIO (local S3)\n")
            f.write(f"MINIO_ROOT_USER={minio_user}\n")
            f.write(f"MINIO_ROOT_PASSWORD={minio_pass}\n")
        f.write("\n# AI Keys\n")
        f.write(f"ANTHROPIC_API_KEY={anthropic_key}\n")
        f.write("\n# Open WebUI\n")
        f.write(f"WEBUI_SECRET_KEY={webui_secret}\n")
        f.write("\n# Superset\n")
        f.write(f"SUPERSET_SECRET_KEY={superset_secret}\n")
        f.write(f"SUPERSET_ADMIN_USER=admin\n")
        f.write(f"SUPERSET_ADMIN_PASSWORD=admin\n")
        f.write("\n# Airflow\n")
        f.write(f"AIRFLOW_FERNET_KEY={airflow_fernet}\n")
        f.write("AIRFLOW_USER=admin\n")
        f.write("AIRFLOW_PASSWORD=admin\n")
        f.write("\n# Keycloak SSO\n")
        f.write("KEYCLOAK_ADMIN_USER=admin\n")
        f.write(f"KEYCLOAK_ADMIN_PASSWORD={keycloak_pass}\n")

    print("\n" + "=" * 60)
    print("  Configuration saved!\n")
    print("  Next steps:")
    print("    make up          →  start core (Mike app)")
    print("    make up-ai       →  + AI stack (Qdrant, RAG, Mem0, Ollama…)")
    print("    make up-data     →  + Data engineering (Airflow, Spark, Livy)")
    print("    make up-bi       →  + BI (Superset)")
    print("    make up-full     →  everything")
    print("=" * 60)


if __name__ == "__main__":
    run()
