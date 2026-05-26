#!/usr/bin/env bash
set -euo pipefail

# Wait for Postgres to be ready using pg_isready
if [ -n "${DATABASE_URL:-}" ]; then
  # extract host and port from DATABASE_URL (very simple parse for common form)
  # expected: postgresql+asyncpg://user:pass@host:port/dbname
  url="$DATABASE_URL"
  host_port=$(echo "$url" | sed -E 's#.*@([^/]+).*#\1#')
  host=$(echo "$host_port" | cut -d: -f1)
  port=$(echo "$host_port" | cut -d: -f2)
  if [ -z "$host" ] || [ -z "$port" ]; then
    echo "DATABASE_URL not recognized for waiting, starting immediately"
  else
    echo "Waiting for Postgres at $host:$port..."
    until pg_isready -h "$host" -p "$port" -q; do
      echo "Postgres not ready, sleeping 1s..."
      sleep 1
    done
    echo "Postgres is ready"
  fi
else
  echo "DATABASE_URL not set — starting without DB wait"
fi

# Run the requested command
exec "$@"
