// CI pipeline for the TV Series Search app.
//
// The only thing the agent needs installed is Docker (with the Compose v2
// plugin) and curl: every build step runs inside a container, so the VM never
// needs Python 3.12, Node or a Postgres client of its own.
pipeline {
    agent any

    options {
        // The stack publishes a fixed port (7777) and uses one Compose project
        // name, so two builds must not overlap on the same agent.
        disableConcurrentBuilds()
        timeout(time: 40, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        // Keeps `docker compose down -v` scoped to this job's containers,
        // volumes and network.
        COMPOSE_PROJECT_NAME = 'tvseries-ci'
        PYTHON_IMAGE = 'python:3.12-slim'
        BASE_URL = 'http://localhost:7777'
        TEST_DB = 'tvseries_test'
    }

    stages {
        stage('Prepare') {
            steps {
                sh '''
                    set -eu
                    for tool in docker curl; do
                        command -v "$tool" >/dev/null 2>&1 || {
                            echo "required tool not installed on the agent: $tool" >&2
                            exit 1
                        }
                    done
                    docker version --format 'docker {{.Server.Version}}'
                    docker compose version

                    mkdir -p reports .ci-cache
                    rm -rf reports/*
                '''
            }
        }

        stage('Lint') {
            steps {
                sh 'ci/py.sh "ruff check src tests"'
            }
        }

        stage('Unit tests') {
            // Domain + application + interface suites: in-memory fakes, no
            // network and no database. The Postgres-backed tests self-skip here
            // and get their own stage below.
            steps {
                sh '''
                    set -eu
                    ci/py.sh "python -m pytest -q \
                        --junitxml=reports/junit-unit.xml \
                        --cov --cov-report=xml:reports/coverage.xml \
                        --cov-report=term-missing --cov-fail-under=90"
                '''
            }
        }

        stage('Frontend tests') {
            steps {
                sh '''
                    set -eu
                    docker run --rm \
                        --user "$(id -u):$(id -g)" \
                        -v "$PWD/frontend:/frontend" \
                        -v "$PWD/reports:/reports" \
                        -v "$PWD/.ci-cache:/npm-cache" \
                        -e npm_config_cache=/npm-cache \
                        -w /frontend node:22-slim sh -c \
                        'npm ci && npm run test:coverage -- --reporter=default --reporter=junit --outputFile.junit=/reports/junit-frontend.xml'
                '''
            }
        }

        stage('Build image') {
            // Multi-stage build: compiles the Vue frontend, then the Python
            // runtime image. A frontend compile error fails here.
            steps {
                sh 'docker compose build'
            }
        }

        stage('Integration tests') {
            // The same suite's @pytest.mark.integration tests, this time
            // against a real Postgres 16 with the migrations applied.
            steps {
                sh '''
                    set -eu
                    # --wait blocks on the db healthcheck, which probes over TCP
                    # and so stays red until initdb is done (docker-compose.yml
                    # explains why the Unix socket lies about readiness).
                    echo "waiting for Postgres"
                    docker compose up -d --wait db

                    # No `|| true` here: if the test database cannot be created,
                    # this stage fails with the psql error instead of handing
                    # pytest an absent database and going green on 50 skips.
                    exists=$(docker compose exec -T db psql -U app -d postgres \
                        -tAc "SELECT 1 FROM pg_database WHERE datname = '$TEST_DB'")
                    if [ "$exists" != 1 ]; then
                        docker compose exec -T db psql -U app -d postgres \
                            -c "CREATE DATABASE $TEST_DB"
                    fi

                    # Join the Compose network so the test container reaches the
                    # database by its service name.
                    network=$(docker inspect \
                        -f '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{end}}' \
                        "$(docker compose ps -q db)")

                    # REQUIRE_TEST_DATABASE turns the suite's skip-when-no-db
                    # fixture into a failure, so this stage cannot pass without
                    # having actually talked to Postgres.
                    DOCKER_EXTRA_ARGS="--network $network \
                        -e TEST_DATABASE_URL=postgresql://app:app@db:5432/$TEST_DB \
                        -e REQUIRE_TEST_DATABASE=1" \
                        ci/py.sh "python -m pytest -q -m integration \
                            --junitxml=reports/junit-integration.xml"
                '''
            }
        }

        stage('Smoke test') {
            // Boots the delivered stack exactly as a reviewer would
            // (`docker compose up`) and exercises it over HTTP.
            steps {
                sh '''
                    set -eu
                    docker compose up -d
                    ci/smoke.sh | tee reports/smoke.txt
                '''
            }
        }
    }

    post {
        always {
            sh '''
                set +e
                mkdir -p reports
                docker compose logs --no-color --tail 400 > reports/compose-logs.txt 2>&1
                docker compose down -v --remove-orphans
            '''
            junit allowEmptyResults: true, testResults: 'reports/junit-*.xml'
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true, fingerprint: false
        }
    }
}
