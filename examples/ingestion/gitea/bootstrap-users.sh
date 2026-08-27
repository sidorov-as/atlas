#!/bin/sh
set -eu

config=/data/gitea/conf/app.ini

create_or_update_user() {
  username=$1
  password=$2
  email=$3
  admin=$4

  admin_flag=
  if [ "$admin" = true ]; then
    admin_flag=--admin
  fi

  if ! gitea admin user create \
    --config "$config" \
    --username "$username" \
    --password "$password" \
    --email "$email" \
    --must-change-password=false \
    $admin_flag; then
    gitea admin user change-password \
      --config "$config" \
      --username "$username" \
      --password "$password" \
      --must-change-password=false
  fi
}

create_or_update_user \
  "$GITEA_ADMIN_USERNAME" \
  "$GITEA_ADMIN_PASSWORD" \
  "$GITEA_ADMIN_EMAIL" \
  true
create_or_update_user \
  "$ATLAS_GITEA_OPERATOR_USERNAME" \
  "$ATLAS_GITEA_OPERATOR_PASSWORD" \
  "$ATLAS_GITEA_OPERATOR_EMAIL" \
  false
