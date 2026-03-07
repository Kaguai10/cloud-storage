#!/bin/sh
# Wait for PostgreSQL to be ready before starting the app

echo "Waiting for PostgreSQL to be ready..."
HOST="${POSTGRES_HOST:-postgres}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-postgres}"
PASSWORD="${POSTGRES_PASSWORD:-postgres}"
DBNAME="${POSTGRES_DB:-cloudstorage}"
MAX_RETRIES=30
RETRY_INTERVAL=2

for i in $(seq 1 $MAX_RETRIES); do
    if PGPASSWORD="$PASSWORD" psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DBNAME" -c '\q' > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        exit 0
    fi
    echo "PostgreSQL not ready yet, retrying in ${RETRY_INTERVAL}s (attempt $i/$MAX_RETRIES)..."
    sleep $RETRY_INTERVAL
done

echo "ERROR: PostgreSQL did not become ready in time"
exit 1
