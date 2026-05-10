FROM supabase/postgres:15.8.1.060

# Copy the app schema so it runs automatically on first DB init.
# The supabase/postgres base image sets up the auth.* schema before
# any scripts in /docker-entrypoint-initdb.d/ are executed, so
# referencing auth.users here is safe.
COPY ../../backend/migrations/000_one_shot_schema.sql \
     /docker-entrypoint-initdb.d/001_app_schema.sql
