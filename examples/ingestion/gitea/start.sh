#!/bin/sh
set -eu

config=/data/gitea/conf/app.ini
if [ ! -f "$config" ]; then
  mkdir -p "$(dirname "$config")"
  cp /bootstrap/app.ini "$config"
fi

exec /usr/bin/entrypoint /usr/bin/s6-svscan /etc/s6
