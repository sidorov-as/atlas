#!/usr/bin/env python3
"""End-to-end smoke test for the Gitea ingestion example: confirms the
startup bootstrap ingested the three fixture Systems (including a
cross-repository `consumesApis` reference that needs the two-pass startup
ingestion to resolve), that the `booking-db` Resource's `spec.databaseSchema`
declaration produced a parsed `DatabaseSchema` Facet, edits a manifest
through the Gitea API, reruns ingestion, and asserts the edit landed."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

GITEA_ORIGIN = 'http://localhost:18092'
ORG_NAME = 'atlas-demo'
MANIFEST_PATH = 'catalog-info.yaml'
DEFAULT_BRANCH = 'main'


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key] = value
    return values


def gitea_request(
    path: str, *, username: str, password: str, method: str = 'GET', data: Any = None,
) -> Any:
    credentials = f'{username}:{password}'
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '
        + base64.b64encode(credentials.encode()).decode(),
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(
        f'{GITEA_ORIGIN}{path}', data=body, headers=headers, method=method,
    )
    try:
        with urllib.request.urlopen(request) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors='replace')[:500]
        raise AssertionError(
            f'Gitea {method} {path} failed with {error.code}: {detail}',
        ) from error
    return json.loads(payload) if payload else None


def compose(env_file: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['docker', 'compose', '--env-file', str(env_file), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def django_shell(env_file: Path, code: str) -> str:
    result = compose(
        env_file, 'exec', '-T', 'backend', 'sh', '-c',
        '. /run/atlas-ingestion/gitea.env; '
        '. /run/atlas-ingestion/ingestion.env; '
        'export GITEA_CLIENT_ID GITEA_CLIENT_SECRET GITEA_INGESTION_TOKEN; '
        'exec python manage.py shell -c "$1"',
        '--', code,
    )
    return result.stdout.strip().splitlines()[-1]


def system_state(env_file: Path, name: str) -> dict[str, Any]:
    code = f"""
import json
from atlas_plugin_api import KIND_SYSTEM, get_catalog_entity_model
Entity = get_catalog_entity_model()
entity = Entity.objects.filter(kind=KIND_SYSTEM, name={name!r}).first()
print(json.dumps(None if entity is None else {{
    'description': entity.description,
    'isYamlManaged': entity.ingested_from_id is not None,
}}))
"""
    return json.loads(django_shell(env_file, code))


def booking_service_state(env_file: Path) -> dict[str, Any]:
    code = """
import json
from atlas_plugin_api import KIND_COMPONENT, get_catalog_entity_model
Entity = get_catalog_entity_model()
entity = Entity.objects.filter(kind=KIND_COMPONENT, name='booking-service').first()
details = None if entity is None else entity.component_details
print(json.dumps(None if details is None else {
    'consumesApis': sorted(details.consumes_apis.values_list('name', flat=True)),
}))
"""
    return json.loads(django_shell(env_file, code))


def booking_db_schema_state(env_file: Path) -> dict[str, Any]:
    code = """
import json
from atlas_plugin_api import KIND_RESOURCE, get_catalog_entity_model
Entity = get_catalog_entity_model()
entity = Entity.objects.filter(kind=KIND_RESOURCE, name='booking-db').first()
schema = None if entity is None else getattr(entity, 'database_schema', None)
print(json.dumps(None if schema is None else {
    'dialect': schema.dialect,
    'parseStatus': schema.parse_status,
    'tables': sorted(t['name'] for t in schema.parsed_schema.get('tables', [])),
}))
"""
    return json.loads(django_shell(env_file, code))


def main() -> None:
    env_file = Path(os.environ.get('ATLAS_COMPOSE_ENV_FILE', '.env'))
    if not env_file.exists():
        env_file = Path('.env.example')
    env = load_env(env_file)
    admin_username = env['GITEA_ADMIN_USERNAME']
    admin_password = env['GITEA_ADMIN_PASSWORD']

    for name in ('search-discovery', 'payments-payouts', 'booking-reservations'):
        state = system_state(env_file, name)
        assert state is not None, f'System {name!r} was not ingested'
        assert state['isYamlManaged'], f'System {name!r} is not YAML-managed'

    booking = booking_service_state(env_file)
    assert booking is not None, 'booking-service Component was not ingested'
    assert booking['consumesApis'] == ['payments-api', 'search-api'], (
        'booking-service consumesApis did not resolve across repositories '
        f'(got {booking["consumesApis"]!r}); confirm ingest-once ran two passes'
    )

    schema = booking_db_schema_state(env_file)
    assert schema is not None, (
        'booking-db DatabaseSchema Facet was not created; confirm '
        'atlas.database-schema is selected and spec.databaseSchema on '
        'booking-db resolved db/schema.sql'
    )
    assert schema['dialect'] == 'postgresql', f'Unexpected dialect {schema["dialect"]!r}'
    assert schema['parseStatus'] == 'ok', f'Schema parse failed: {schema!r}'
    assert schema['tables'] == [
        'guests', 'hosts', 'listings', 'reservation_events', 'reservations',
    ], f'Unexpected parsed tables {schema["tables"]!r}'

    existing = gitea_request(
        f'/api/v1/repos/{ORG_NAME}/search-discovery/contents/{MANIFEST_PATH}'
        f'?ref={DEFAULT_BRANCH}',
        username=admin_username, password=admin_password,
    )
    content = base64.b64decode(existing['content']).decode()
    marker = f'Smoke-edited description {uuid.uuid4().hex[:8]}'
    updated = content.replace(
        'description: Query, rank, and serve available listings to guests.',
        f'description: {marker}',
    )
    assert updated != content, 'Expected description line was not found in the manifest'
    gitea_request(
        f'/api/v1/repos/{ORG_NAME}/search-discovery/contents/{MANIFEST_PATH}',
        username=admin_username, password=admin_password,
        method='PUT',
        data={
            'content': base64.b64encode(updated.encode()).decode(),
            'sha': existing['sha'],
            'branch': DEFAULT_BRANCH,
            'message': 'Smoke test edit',
        },
    )

    compose(
        env_file, 'exec', '-T', 'backend', 'sh', '-c',
        '. /run/atlas-ingestion/gitea.env; '
        '. /run/atlas-ingestion/ingestion.env; '
        'export GITEA_CLIENT_ID GITEA_CLIENT_SECRET GITEA_INGESTION_TOKEN; '
        'exec python manage.py ingest',
    )

    reingested = system_state(env_file, 'search-discovery')
    assert reingested is not None
    assert reingested['description'] == marker, (
        f'Expected {marker!r} after reingestion, got {reingested["description"]!r}'
    )

    print('Ingestion example smoke test passed.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Ingestion example smoke failed: {error}', file=sys.stderr)
        raise
