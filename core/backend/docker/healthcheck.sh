#!/usr/bin/env sh
set -eu

curl --fail --silent --output /dev/null http://localhost:8000/healthz/
