#!/usr/bin/env bash
# Ensure the Metabase metadata database and user exist during Postgres init.
set -euo pipefail

DB_NAME=${METABASE_DB_NAME:-metabase}
DEFAULT_DB_USER=${PG_USER:-$POSTGRES_USER}
DB_USER=${METABASE_DB_USER:-$DEFAULT_DB_USER}
DB_PASS=${METABASE_DB_PASSWORD:-${PG_PASSWORD:-}}

export PGPASSWORD="${POSTGRES_PASSWORD:-}"

# Create database if missing
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  SELECT 'CREATE DATABASE "${DB_NAME}"'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec
EOSQL

# Create user if different from the main postgres user
if [ "$DB_USER" != "$POSTGRES_USER" ]; then
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
        EXECUTE format('CREATE ROLE "%s" LOGIN PASSWORD %L', '${DB_USER}', '${DB_PASS}');
      END IF;
    END$$;
EOSQL
fi

# Ensure permissions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  ALTER DATABASE "${DB_NAME}" OWNER TO "${DB_USER}";
  GRANT ALL PRIVILEGES ON DATABASE "${DB_NAME}" TO "${DB_USER}";
EOSQL
