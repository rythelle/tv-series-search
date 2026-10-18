#!/usr/bin/env sh
# Run a command against the project's Python 3.12 toolchain inside a throwaway
# container, so the CI machine only ever needs Docker installed.
#
#   ci/py.sh "python -m pytest -q"
#
# The workspace is mounted at /workspace and HOME points inside it, so pip's
# cache and its --user install survive between builds (in .ci-cache/) and
# nothing is written outside the workspace. Extra `docker run` flags — a
# network to join, more environment variables — come from DOCKER_EXTRA_ARGS.
set -eu

[ $# -ge 1 ] || { echo "usage: ci/py.sh <command>" >&2; exit 2; }

mkdir -p .ci-cache

# DOCKER_EXTRA_ARGS is deliberately left unquoted so it word-splits into flags.
# shellcheck disable=SC2086
exec docker run --rm \
    -u "$(id -u):$(id -g)" \
    -e HOME=/workspace/.ci-cache \
    -e PATH=/workspace/.ci-cache/.local/bin:/usr/local/bin:/usr/bin:/bin \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PIP_DISABLE_PIP_VERSION_CHECK=1 \
    -v "$(pwd):/workspace" \
    -w /workspace \
    ${DOCKER_EXTRA_ARGS:-} \
    "${PYTHON_IMAGE:-python:3.12-slim}" \
    sh -euc "pip install --user --quiet -r requirements-dev.txt && $*"
