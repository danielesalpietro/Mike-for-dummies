#!/bin/bash
set -e

# Create the roles that GoTrue and PostgREST require.
# POSTGRES_PASSWORD is injected by the postgres Docker entrypoint.
psql -v ON_ERROR_STOP=1 \
     --username "${POSTGRES_USER:-postgres}" \
     --dbname   "${POSTGRES_DB:-postgres}" <<EOSQL

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- PostgREST roles
CREATE ROLE anon          NOLOGIN  NOINHERIT;
CREATE ROLE authenticated NOLOGIN  NOINHERIT;
CREATE ROLE service_role  NOLOGIN  NOINHERIT BYPASSRLS;

-- authenticator is the login role PostgREST uses to switch to anon/authenticated
CREATE ROLE authenticator NOINHERIT LOGIN PASSWORD '${POSTGRES_PASSWORD:-postgres}';
GRANT anon          TO authenticator;
GRANT authenticated TO authenticator;
GRANT service_role  TO authenticator;

-- GoTrue auth admin role
CREATE ROLE supabase_auth_admin NOINHERIT CREATEROLE LOGIN
    PASSWORD '${POSTGRES_PASSWORD:-postgres}';

-- Auth schema — GoTrue will run its own migrations here
CREATE SCHEMA IF NOT EXISTS auth AUTHORIZATION supabase_auth_admin;
GRANT ALL PRIVILEGES ON DATABASE postgres TO supabase_auth_admin;
GRANT ALL ON SCHEMA auth TO supabase_auth_admin;

-- Public schema grants for PostgREST
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES    TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON ROUTINES  TO anon, authenticated, service_role;

EOSQL
