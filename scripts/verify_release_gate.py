#!/usr/bin/env python3
"""Fail-closed CI evidence gate. Does not deploy, merge, or access live services."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'artifacts' / 'validation' / 'release-gate.json'


def evaluate(ci_result: str, recovery_result: str, config: dict) -> list[str]:
    failures = []
    if ci_result != 'success':
        failures.append('Python/PostgreSQL/assessment/Chromium acceptance job not successful')
    if recovery_result != 'success':
        failures.append('Disposable database recovery rehearsal not successful')
    services = config.get('services') if isinstance(config, dict) else None
    if not isinstance(services, list) or len(services) != 1:
        failures.append('Render blueprint must contain exactly one static website')
        return failures
    site = services[0]
    if not isinstance(site, dict):
        failures.append('Render blueprint service is invalid')
        return failures
    if site.get('type') != 'web' or site.get('runtime') != 'static':
        failures.append('Render blueprint must never define an API or dynamic service')
    if site.get('staticPublishPath') != './apps/site':
        failures.append('Render static publish path differs from reviewed website')
    if site.get('autoDeployTrigger') != 'off':
        failures.append('Render automatic deployments must be disabled')
    for field in ('envVars', 'startCommand', 'disk', 'databases', 'previews'):
        if field in site:
            failures.append(f'Forbidden Render service field: {field}')
    for field in ('databases', 'envVarGroups'):
        if field in config:
            failures.append(f'Forbidden top-level Render field: {field}')
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--test-result', required=True)
    parser.add_argument('--recovery-result', required=True)
    args = parser.parse_args(argv)
    try:
        with (ROOT / 'render.yaml').open(encoding='utf-8') as file:
            config = yaml.safe_load(file)
        failures = evaluate(args.test_result, args.recovery_result, config)
    except (OSError, yaml.YAMLError):
        failures = ['Render blueprint missing or cannot be parsed']
    result = 'PASS' if not failures else 'FAIL'
    report = {
        'schema_version': 1,
        'gate': 'ci-release-evidence',
        'result': result,
        'checks': {
            'functional_assessment_and_browser': args.test_result,
            'recovery_rehearsal': args.recovery_result,
            'render_blueprint': 'PASS' if not [x for x in failures if x.startswith(('Render', 'Forbidden'))] else 'FAIL',
        },
        'failures': failures,
        'deploy_performed': False,
        'customer_access_enabled': False,
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    summary_path = os.getenv('GITHUB_STEP_SUMMARY')
    message = [f'## MetaAutomate release evidence gate: {result}',
               '| Evidence | Result |', '|---|---|',
               f'| Functional/browser CI | {args.test_result} |',
               f'| Disposable recovery CI | {args.recovery_result} |',
               f'| Render blueprint | {report["checks"]["render_blueprint"]} |',
               '', '**No deployment or customer-access change performed.**',
               'Human approval and enabled required-status-check rules are separate release gates.']
    if failures:
        message.extend(['', '**Blocked:**'] + [f'- {why}' for why in failures])
    if summary_path:
        with open(summary_path, 'a', encoding='utf-8') as file:
            file.write('\n'.join(message)+'\n')
    print('\n'.join(message))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
