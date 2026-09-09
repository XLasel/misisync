"""Exercise deployment scripts with fake Docker/cron; never touch a real server or certificate."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

REPO = Path(__file__).resolve().parents[2]



@pytest.fixture
def sandbox(tmp_path):
    root = tmp_path / "app with spaces"
    shutil.copytree(REPO / 'deploy', root / 'deploy', ignore=shutil.ignore_patterns('conf', 'www', 'active', '*.log'))
    (root / '.env').write_text('DOMAIN=schedule.example.test\n')
    fakebin = tmp_path / 'bin'
    fakebin.mkdir()
    env = {**os.environ, 'PATH': f'{fakebin}:{os.environ["PATH"]}', 'MISISYNC_DEPLOY_LOCKED': '1', 'TEST_ROOT': str(root)}
    # This test suite also runs on macOS, which has no sha256sum/flock.
    for command, body in {
        'systemctl': 'exit "${CRON_ACTIVE_EXIT:-0}"',
        'sha256sum': 'cat >/dev/null; echo "123456789abc  -"',
        'docker': '''printf '%s\\n' "$*" >> "$TEST_ROOT/docker.calls"
case "$*" in
  *" renew "*)
    if [ "${RENEWED:-0}" = 1 ]; then touch "$TEST_ROOT/deploy/certbot/www/.reload-required"; fi
    exit "${CERTBOT_EXIT:-0}" ;;
  *"nginx -s reload"*) exit "${RELOAD_EXIT:-0}" ;;
esac''',
        'crontab': '''if [ "$1" = -l ]; then
  if [ -f "$TEST_ROOT/cron" ]; then cat "$TEST_ROOT/cron"; else echo 'no crontab for test' >&2; exit 1; fi
else cp "$1" "$TEST_ROOT/cron"; fi''',
    }.items():
        p = fakebin / command
        p.write_text('#!/bin/sh\nset -eu\n' + body + '\n')
        p.chmod(0o755)
    return root, env


def run(sandbox, script, *args, **overrides):
    root, env = sandbox
    return subprocess.run(['bash', str(root / 'deploy' / script), *args], env={**env, **overrides}, capture_output=True, text=True)


def test_cron_install_is_idempotent_and_preserves_other_jobs(sandbox):
    root, _ = sandbox
    existing = '0 1 * * * echo unrelated\n'
    (root / 'cron').write_text(existing)
    for _ in range(2):
        result = run(sandbox, 'install-renewal.sh')
        assert result.returncode == 0, result.stderr
    cron = (root / 'cron').read_text()
    assert cron.startswith(existing)
    assert cron.count('# misisync-renew-') == 1
    assert f"'{root}/deploy/renew-cert.sh'" in cron


def test_noop_renewal_does_not_reload_nginx(sandbox):
    root, _ = sandbox
    result = run(sandbox, 'renew-cert.sh')
    assert result.returncode == 0, result.stderr
    assert 'nginx -s reload' not in (root / 'docker.calls').read_text()


def test_failed_reload_is_retried_even_when_next_renewal_is_a_noop(sandbox):
    root, _ = sandbox
    first = run(sandbox, 'renew-cert.sh', RENEWED='1', RELOAD_EXIT='1')
    assert first.returncode != 0
    marker = root / 'deploy/certbot/www/.reload-required'
    assert marker.exists()
    second = run(sandbox, 'renew-cert.sh')
    assert second.returncode == 0, second.stderr
    assert not marker.exists()
    assert (root / 'docker.calls').read_text().count('nginx -s reload') == 2


def test_renewal_failure_is_reported_and_dry_run_does_not_reload(sandbox):
    root, _ = sandbox
    assert run(sandbox, 'renew-cert.sh', CERTBOT_EXIT='1').returncode == 1
    dry_run = run(sandbox, 'renew-cert.sh', '--dry-run', RENEWED='1')
    assert dry_run.returncode == 0, dry_run.stderr
    assert 'nginx -s reload' not in (root / 'docker.calls').read_text()


def test_invalid_domain_fails_before_docker(sandbox):
    root, _ = sandbox
    (root / '.env').write_text("DOMAIN='example.test; injected'\n")
    assert run(sandbox, 'renew-cert.sh').returncode != 0
    assert not (root / 'docker.calls').exists()


def test_runtime_secrets_are_ignored_by_git():
    paths = ['deploy/certbot/conf/accounts/private_key.json', 'deploy/certbot/conf/archive/domain/privkey1.pem',
             'deploy/certbot/www/.reload-required', 'deploy/certbot/renew.log', '.env.production', '.deploy.lock']
    for path in paths:
        result = subprocess.run(['git', 'check-ignore', '--no-index', '-q', path], cwd=REPO)
        assert result.returncode == 0, path


def test_stopped_cron_is_not_reported_as_working_automation(sandbox):
    result = run(sandbox, 'install-renewal.sh', CRON_ACTIVE_EXIT='1')
    assert result.returncode != 0
    assert 'Enable cron' in result.stderr
