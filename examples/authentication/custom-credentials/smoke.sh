#!/bin/sh
set -eu

compose_env_file=${ATLAS_COMPOSE_ENV_FILE:-./.env}
if [ ! -f "$compose_env_file" ]; then
  compose_env_file=./.env.example
fi

exec python3 ./smoke.py "$compose_env_file"
