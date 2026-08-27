#!/usr/bin/env python3
"""Run authentication example smoke tests and collect redacted CI diagnostics."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

SENSITIVE_ENV_NAME = re.compile(
    r"(?:PASSWORD|SECRET|TOKEN|PRIVATE_KEY|BIND_DN|CREDENTIAL)", re.IGNORECASE
)
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
URL_SECRET = re.compile(
    r"(?i)([?&](?:code|state|token|access_token|refresh_token|id_token|"
    r"client_secret|session_state)=)[^&#\s]+"
)
HEADER_SECRET = re.compile(r"(?im)^(\s*(?:authorization|cookie|set-cookie)\s*:\s*).*$")
ASSIGNMENT_SECRET = re.compile(
    r"(?im)((?:[\"']?[A-Za-z0-9_-]*(?:password|secret|token|private[_-]?key|"
    r"credential|sessionid|csrftoken)[A-Za-z0-9_-]*[\"']?)\s*[=:]\s*)"
    r"([^\s,;]+|\"[^\"]*\"|'[^']*')"
)


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text().splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: expected NAME=value")
        name, value = line.split("=", 1)
        values[name] = value
    return values


def sensitive_values(environment: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                value
                for name, value in environment.items()
                if value and SENSITIVE_ENV_NAME.search(name)
            },
            key=len,
            reverse=True,
        )
    )


def redact(text: str, *, secrets: Sequence[str]) -> str:
    for secret in secrets:
        text = text.replace(secret, "<redacted>")
    text = JWT.sub("<redacted-jwt>", text)
    text = URL_SECRET.sub(r"\1<redacted>", text)
    text = HEADER_SECRET.sub(r"\1<redacted>", text)
    return ASSIGNMENT_SECRET.sub(r"\1<redacted>", text)


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def write_result(
    path: Path,
    result: subprocess.CompletedProcess[str],
    *,
    secrets: Sequence[str],
) -> str:
    content = (
        f"exit_code={result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
    )
    safe = redact(content, secrets=secrets)
    path.write_text(safe)
    return safe


def compose_command(env_file: Path, *args: str) -> list[str]:
    return ["docker", "compose", "--env-file", str(env_file), *args]


def run_smoke(example: Path, env_file: Path, output: Path) -> int:
    values = load_env(env_file)
    environment = os.environ.copy()
    environment["ATLAS_COMPOSE_ENV_FILE"] = str(env_file)
    result = run_command(["./smoke.sh"], cwd=example, environment=environment)
    safe = write_result(output, result, secrets=sensitive_values(values))
    stream = sys.stdout if result.returncode == 0 else sys.stderr
    print(safe, file=stream, end="")
    return result.returncode


def collect_diagnostics(example: Path, env_file: Path, output_dir: Path) -> int:
    values = load_env(env_file)
    secrets = sensitive_values(values)
    output_dir.mkdir(parents=True, exist_ok=True)
    commands = {
        "compose-ps.txt": compose_command(env_file, "ps", "--all"),
        "compose-images.txt": compose_command(env_file, "images"),
        "compose-logs.txt": compose_command(
            env_file, "logs", "--no-color", "--timestamps"
        ),
    }
    failed = False
    for filename, command in commands.items():
        result = run_command(command, cwd=example)
        write_result(output_dir / filename, result, secrets=secrets)
        failed = failed or result.returncode != 0
    return int(failed)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "collect"))
    parser.add_argument("--example", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    example = args.example.resolve()
    env_file = (
        args.env_file.resolve()
        if args.env_file.is_absolute()
        else (example / args.env_file).resolve()
    )
    output = args.output.resolve()
    if args.action == "run":
        output.parent.mkdir(parents=True, exist_ok=True)
        return run_smoke(example, env_file, output)
    return collect_diagnostics(example, env_file, output)


if __name__ == "__main__":
    sys.exit(main())
