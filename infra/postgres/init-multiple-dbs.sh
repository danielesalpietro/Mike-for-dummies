#!/bin/bash
# Creates additional databases needed by Airflow, MLflow, Superset, and Keycloak.
# Runs automatically on first postgres container startup via docker-entrypoint-initdb.d.
set -e

create_db_if_missing() {
    local db=$1
    echo "Creating database '$db' if it does not exist..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $db'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
}

create_db_if_missing airflow
create_db_if_missing mlflow
create_db_if_missing superset
create_db_if_missing keycloak

echo "All databases ready."
