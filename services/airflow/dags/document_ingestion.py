"""
DAG: document_ingestion
────────────────────────
Pulls documents from the Mike PostgreSQL database, converts them to plain
text (via Livy/Spark if available, otherwise directly), and ingests the
text chunks into the Qdrant vector store via the RAG service.

Schedule: every hour.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

RAG_URL = "http://rag-service:8001"
CHUNK_SIZE = 800   # characters per chunk
CHUNK_OVERLAP = 100

default_args = {
    "owner": "mike",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def check_rag_health(**_) -> None:
    resp = requests.get(f"{RAG_URL}/health", timeout=10)
    resp.raise_for_status()
    logger.info("RAG service healthy: %s", resp.json())


def ingest_sample_documents(**context) -> None:
    """
    In a real pipeline this task would:
      1. Query the mike.documents table via psycopg2 or a Livy Spark job.
      2. Extract text from each document (PDF/DOCX already handled by backend).
      3. Chunk and embed via the RAG service.

    This sample pushes a few synthetic documents to demonstrate the flow.
    """
    sample_docs = [
        {
            "document_id": "sample-001",
            "text": (
                "Quarterly sales report Q3 2025. Total revenue: €4.2M, "
                "up 12% YoY. Top products: Enterprise License (+18%), "
                "Professional Services (+9%). EMEA region leads growth."
            ),
            "metadata": {"source": "sample", "type": "report", "quarter": "Q3-2025"},
        },
        {
            "document_id": "sample-002",
            "text": (
                "Company policy update: remote work policy revised. "
                "Employees may work remotely up to 3 days per week. "
                "Core hours 10:00–15:00 CET remain mandatory."
            ),
            "metadata": {"source": "sample", "type": "policy"},
        },
    ]

    ingested = 0
    for doc in sample_docs:
        chunks = _chunk_text(doc["text"])
        for i, chunk in enumerate(chunks):
            payload = {
                "document_id": f"{doc['document_id']}-chunk-{i}",
                "text": chunk,
                "metadata": {**doc["metadata"], "chunk_index": i, "parent_id": doc["document_id"]},
            }
            resp = requests.post(f"{RAG_URL}/ingest", json=payload, timeout=30)
            resp.raise_for_status()
            ingested += 1

    logger.info("Ingested %d chunks into Qdrant", ingested)
    return ingested


def log_stats(**_) -> None:
    resp = requests.get(f"{RAG_URL}/stats", timeout=10)
    if resp.ok:
        logger.info("Qdrant collection stats: %s", resp.json())


with DAG(
    dag_id="document_ingestion",
    description="Ingest Mike documents into the Qdrant vector store for RAG",
    default_args=default_args,
    start_date=datetime(2025, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["mike", "rag", "ingestion"],
) as dag:

    t_health = PythonOperator(
        task_id="check_rag_health",
        python_callable=check_rag_health,
    )

    t_ingest = PythonOperator(
        task_id="ingest_documents",
        python_callable=ingest_sample_documents,
    )

    t_stats = PythonOperator(
        task_id="log_collection_stats",
        python_callable=log_stats,
    )

    t_health >> t_ingest >> t_stats
