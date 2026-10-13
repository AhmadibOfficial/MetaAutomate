"""No Docker, database, network or deployment needed for these gate unit tests."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


local = load('verify_local_gate')
release = load('verify_release_gate')
SAFE = {'services': [{'type': 'web', 'runtime': 'static',
                      'staticPublishPath': './apps/site', 'autoDeployTrigger': 'off'}]}


def test_release_gate_fail_closed_on_ci_errors():
    assert release.evaluate('success', 'success', SAFE) == []
    assert release.evaluate('failure', 'success', SAFE)
    assert release.evaluate('skipped', 'success', SAFE)
    assert release.evaluate('success', 'cancelled', SAFE)


@pytest.mark.parametrize('mutations', [
    {'runtime': 'docker'}, {'autoDeployTrigger': 'commit'},
    {'envVars': []}, {'startCommand': 'uvicorn app.main:app'},
    {'staticPublishPath': './apps/api'}, {'previews': {}},
])
def test_release_policy_blocks_unsafe_blueprints(mutations):
    assert release.evaluate('success', 'success', {'services': [{**SAFE['services'][0], **mutations}]})


def test_release_policy_blocks_additional_services():
    assert release.evaluate('success', 'success', {'services': SAFE['services'] * 2})
    assert release.evaluate('success', 'success', {'services': SAFE['services'], 'databases': [{}]})


def test_local_security_schema_must_exactly_match():
    local.evaluate_security('metaautomate|true|true|true|true|true|false|false|1|2')
    with pytest.raises(local.GateError):
        local.evaluate_security('metaautomate|true|true|false|true|true|false|false|1|2')
    with pytest.raises(local.GateError):
        local.evaluate_security('metaautomate|true|true|true|true|true|true|false|1|2')


def test_local_gate_rejects_target_override_without_docker(monkeypatch):
    monkeypatch.setenv('DOCKER_HOST', 'tcp://example.invalid:2375')
    def never(*args, **kwargs):
        raise AssertionError('Docker should not be called for overridden targets')
    monkeypatch.setattr(local, 'command', never)
    with pytest.raises(local.GateError, match='overrides prohibited'):
        local.run_checks()
