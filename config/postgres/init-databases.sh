#!/bin/bash
# This project was developed with assistance from AI tools.
# Creates additional databases needed by services sharing the postgres container.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE langfuse;
EOSQL
