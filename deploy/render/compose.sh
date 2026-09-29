#!/usr/bin/env bash
# Regenerate the Render demo lock and backend plugin module from manifest.yaml.
# The Dockerfile copies selected_plugins.py over core/backend's default one.
set -euo pipefail
cd "$(dirname "$0")/../.."
compose() { uv run --project composer atlas-compose "$@"; }
compose resolve deploy/render/manifest.yaml -o deploy/render/lock.yaml
compose validate deploy/render/manifest.yaml deploy/render/lock.yaml
compose generate backend deploy/render/lock.yaml -o deploy/render/selected_plugins.py
