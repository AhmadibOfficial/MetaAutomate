#!/usr/bin/env python3
"""Read-only local Operational Core validation; never runs migrations or test writes.

Run from an existing Kali checkout with make verify-local. This is a local
readiness check; functional mutation/browser acceptance runs only in disposable CI.
The report intentionally contains no credentials, raw URLs or secret-bearing logs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / '.buildlog' / 'validation' / 'local-gate.json'
ENDPOINT = 'http://127.0.0.1:8000'
OVERRIDES = ('DOCKER_HOST', 'DOCKER_CONTEXT', 'COMPOSE_FILE', 'COMPOSE_PROJECT_NAME')


class GateError(Exception):
    pass


def command(*args: str, timeout: int = 15) -> str:
    try:
        run = subprocess.run(args, cwd=ROOT, text=True, capture_output=True,
                             timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateError(f'Command unavailable or timed out: {args[0]}') from exc
    if run.returncode != 0:
        # NEVER print command stderr; it may contain connection strings.
        raise GateError(f'Command failed (exit {run.returncode}): {args[0]}')
    return run.stdout.strip()


def sql(query: str) -> str:
    return command('docker', 'compose', 'exec', '-T', 'postgres', 'psql',
                   '-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
                   '-U', 'metaautomate', '-d', 'metaautomate', '-c', query)


def http_json(path: str, *, expected: int, attempts: int = 1) -> dict:
    for i in range(attempts):
        try:
            with urlopen(ENDPOINT + path, timeout=3) as response:
                status = response.status
                payload = json.load(response) if status == 200 else {}
        except HTTPError as error:
            status, payload = error.code, {}
        except (URLError, TimeoutError, ValueError, OSError):
            status, payload = None, {}
        if status == expected:
            return payload
        if i < attempts - 1:
            time.sleep(1)
    raise GateError(f'HTTP check failed: {path} expected {expected}; got {status}')


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def evaluate_security(values: str) -> None:
    expected = 'metaautomate|true|true|true|true|true|false|false|1|2'
    require(values == expected, 'Migration 011 security/RLS/runtime-grant check failed')


def run_checks() -> dict:
    require(all(not os.getenv(key) for key in OVERRIDES), 'Docker/Compose target overrides prohibited')
    env = ROOT / '.env'
    require(env.is_file() and not env.is_symlink(), 'Private local .env must exist as regular file')
    require(command('docker', 'context', 'inspect', '--format',
                    '{{ (index .Endpoints "docker").Host }}').startswith('unix://'),
            'Only local Unix-socket Docker is approved')
    require(command('docker', 'compose', 'ps', '-q', 'postgres') != '',
            'Existing PostgreSQL must be running (no auto-start)')
    postgres_id = command('docker', 'compose', 'ps', '-q', 'postgres')
    mounts = command('docker', 'inspect', postgres_id, '--format',
                     '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')
    require(mounts == 'metaautomate-github_pgdata', 'Unexpected PostgreSQL data volume')
    require(command('docker', 'compose', 'ps', '-q', 'api') != '',
            'Existing API must be running (no auto-start)')
    require(command('docker', 'compose', 'port', 'api', '8000') == '127.0.0.1:8000',
            'API must be bound to 127.0.0.1:8000 only')
    security = sql("""SELECT current_database() || '|' ||
        (to_regclass('public.digital_assessments') IS NOT NULL)::text || '|' ||
        c.relrowsecurity::text || '|' || c.relforcerowsecurity::text || '|' ||
        has_table_privilege('metaautomate_runtime', 'public.digital_assessments', 'SELECT')::text || '|' ||
        has_table_privilege('metaautomate_runtime', 'public.digital_assessments', 'INSERT')::text || '|' ||
        has_table_privilege('metaautomate_runtime', 'public.digital_assessments', 'UPDATE')::text || '|' ||
        has_table_privilege('metaautomate_runtime', 'public.digital_assessments', 'DELETE')::text || '|' ||
        (SELECT count(*) FROM pg_policies WHERE tablename='digital_assessments'
          AND policyname='tenant_digital_assessments')::text || '|' ||
        (SELECT count(*) FROM pg_trigger WHERE tgrelid='public.digital_assessments'::regclass
          AND tgname IN ('trg_digital_assessments_no_update', 'trg_digital_assessments_no_delete')
          AND tgenabled <> 'D')::text
        FROM pg_class c WHERE c.oid='public.digital_assessments'::regclass;""")
    evaluate_security(security)
    counts_query = "SELECT (SELECT count(*) FROM organizations)::text || ',' || (SELECT count(*) FROM objectives)::text || ',' || (SELECT count(*) FROM audit_events)::text || ',' || (SELECT count(*) FROM capability_executions)::text;"
    before = sql(counts_query)
    require(len(before.split(',')) == 4 and all(x.isdecimal() for x in before.split(',')),
            'Unexpected business record count output')
    require(http_json('/health', expected=200, attempts=12) ==
            {'status': 'ok', 'service': 'metaautomate-api'}, 'Unexpected API health response')
    require(http_json('/ready', expected=200, attempts=4) ==
            {'status': 'ready', 'database': 'connected'}, 'Unexpected database readiness response')
    http_json('/v1/assessments/questions', expected=401)
    http_json('/v1/workspace/session', expected=401)
    after = sql(counts_query)
    require(after == before, 'Existing business record counts changed during read-only checks')
    return {'database': 'metaautomate', 'volume': mounts,
            'migration_011': 'installed', 'rls': 'forced',
            'runtime_permissions': 'select_insert_only', 'report_triggers': 'enabled',
            'api_health': 'healthy', 'database_ready': 'ready',
            'unauthenticated_assessment': 'denied', 'unauthenticated_session': 'denied',
            'record_counts_unchanged': True}


def write_report(report: dict) -> None:
    folder = REPORT.parent
    require(not folder.is_symlink(), 'Report directory must not be a symlink')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(folder, 0o700)
    require(not REPORT.is_symlink(), 'Report file must not be a symlink')
    tmp = folder / '.local-gate.tmp'
    require(not tmp.is_symlink(), 'Temporary report must not be a symlink')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as file:
        json.dump(report, file, indent=2, sort_keys=True)
        file.write('\n')
    os.replace(tmp, REPORT)
    os.chmod(REPORT, 0o600)


def main() -> int:
    report = {'schema_version': 1, 'gate': 'local-readiness',
              'generated_at': datetime.now(timezone.utc).isoformat(),
              'result': 'FAIL'}
    try:
        report['checks'] = run_checks()
        report['result'] = 'PASS'
    except GateError as err:
        report['failure'] = str(err)
    try:
        write_report(report)
    except (GateError, OSError):
        print('WARNING: Could not save the local gate report', file=sys.stderr)
    print(f"{report['result']}: MetaAutomate local readiness gate")
    if report['result'] != 'PASS':
        print(f"Reason: {report['failure']}", file=sys.stderr)
        print('No migration, test write, service restart, or credential change performed.')
        return 1
    print('Verified: local Docker, volume, schema security, API, authorization denials, stable counts')
    print('No test data written; comprehensive functional/browser acceptance runs in disposable CI.')
    print('Report: .buildlog/validation/local-gate.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
