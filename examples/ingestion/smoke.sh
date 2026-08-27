#!/bin/sh
set -eu

compose_env_file=${ATLAS_COMPOSE_ENV_FILE:-./.env}
if [ ! -f "$compose_env_file" ]; then
  compose_env_file=./.env.example
fi

ATLAS_COMPOSE_ENV_FILE=$compose_env_file python3 ./smoke.py
