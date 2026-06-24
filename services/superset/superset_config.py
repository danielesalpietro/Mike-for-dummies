"""
Apache Superset configuration for Mike Enterprise AI Platform.
Mounted at /app/pythonpath/superset_config.py inside the container.
"""

import os

# ── Core ──────────────────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me-in-production")

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://mike:mike_secret@postgres:5432/superset",
)

# ── Cache (Redis) ─────────────────────────────────────────────────────────────

REDIS_URL = os.environ.get("REDIS_URL", "redis://:redis_secret@redis:6379/1")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_URL": REDIS_URL,
}

DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
    "CACHE_KEY_PREFIX": "superset_data_",
    "CACHE_REDIS_URL": REDIS_URL,
}

# ── Feature flags ─────────────────────────────────────────────────────────────

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "GLOBAL_ASYNC_QUERIES": False,   # set True + Celery for production
    "DASHBOARD_RBAC": True,
    "EMBEDDABLE_CHARTS": True,
    "ALERTS_ATTACH_REPORTS": True,
}

# ── Row-level security ────────────────────────────────────────────────────────

ROW_LEVEL_SECURITY_FILTER_TEMPLATE = True

# ── Allow iframe embedding ────────────────────────────────────────────────────

# Needed if you want to embed Superset charts inside Mike's frontend.
HTTP_HEADERS = {"X-Frame-Options": "SAMEORIGIN"}

# ── Logging ───────────────────────────────────────────────────────────────────

ENABLE_PROXY_FIX = True
