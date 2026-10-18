#!/usr/bin/env sh
# Run Postgres integration tests inside the Compose network.
set -eu

# --wait blocks on the db healthcheck. It probes over TCP because during
# initdb the entrypoint's temporary server answers pg_isready on the Unix
# socket before the database exists (see docker-compose.yml).
docker compose up -d --wait db

exists=$(docker compose exec -T db psql -U app -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = 'tvseries_test'")
if [ "$exists" != 1 ]; then
    docker compose exec -T db psql -U app -d postgres -c \
        "CREATE DATABASE tvseries_test"
fi

db_container=$(docker compose ps -q db)
network=$(docker inspect \
    -f '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{end}}' \
    "$db_container")
# REQUIRE_TEST_DATABASE makes an unreachable database a failure rather than a
# suite of silent skips — this script exists to run against a real Postgres.
DOCKER_EXTRA_ARGS="--network $network \
    -e TEST_DATABASE_URL=postgresql://app:app@db:5432/tvseries_test \
    -e REQUIRE_TEST_DATABASE=1" \
    ci/py.sh "python -m pytest -q -m integration"
