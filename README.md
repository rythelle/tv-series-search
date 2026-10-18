# TV Series Search

An app to search TV series, browse episodes by season, track watched episodes, post comments, and generate insights. It uses FastAPI, Vue 3, and Postgres.

## Run

Requires Docker with Compose:

```bash
docker compose up --build
```

Open <http://localhost:7777>. To stop the app, run `docker compose down`.
No AI key is required: without `AI_API_KEY`, insights use the built-in heuristic generator.

## Configuration

Without `.env`, Compose uses the `${VAR:-default}` values in `docker-compose.yml`.
If `.env` exists, Compose uses its values for the variables listed under
`services.app.environment` and passes them to the container. Variables set in
your shell take precedence over `.env`.

To customize the configuration:

```bash
cp .env.example .env
```

Edit `.env` and recreate the container with `docker compose up -d --build`.
The file is optional and ignored by Git. To use an AI provider, set
`AI_PROVIDER`, `AI_API_KEY`, and `AI_MODEL` in it. Postgres uses the credentials
defined in the Compose file. `SEED_PAGES` controls the size of the initial
browsing list; search also queries TVMaze to reach the rest of the catalog.

## Tests

Use Python 3.12 in the virtual environment and Node 22 for frontend tests:

```bash
.venv/bin/python -m pytest -q
make test-integration                 # requires Docker; uses Postgres on the Compose network
cd frontend && npm ci && npm run test:coverage
```

Integration tests are skipped in the quick suite when no database is reachable.
The pipeline is defined in [`Jenkinsfile`](./Jenkinsfile).
