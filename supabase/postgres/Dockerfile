FROM postgres:15-alpine

# Install pgcrypto (needed by the app schema — gen_random_uuid, etc.)
RUN apk add --no-cache postgresql-contrib

# 01_roles.sh creates the Supabase roles (anon, authenticated, authenticator,
# supabase_auth_admin) that GoTrue and PostgREST expect to find.
COPY supabase/postgres/init/01_roles.sh /docker-entrypoint-initdb.d/01_roles.sh
RUN chmod +x /docker-entrypoint-initdb.d/01_roles.sh
