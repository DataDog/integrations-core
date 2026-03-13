# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.config.secret_command import SecretCommandError


def test_startup_missing_required_secret_is_actionable_without_traceback(ddev, config_file):
    config_file.model.github.user = 'test-user'
    config_file.save()

    result = ddev('status')

    assert result.exit_code == 1, result.output
    assert 'Missing required secret: github.token' in result.output
    assert 'Code: missing-required-secret' in result.output
    assert 'Sources: command=absent, literal=absent, env=DD_GITHUB_TOKEN|GH_TOKEN|GITHUB_TOKEN:absent' in result.output
    assert 'Set *_command, configure a literal secret, or export the expected environment variable.' in result.output
    assert 'Traceback' not in result.output


def test_startup_trust_blocked_secret_points_to_allow_deny_workflow(ddev, config_file, helpers, overrides_config):
    config_file.model.github.user = 'test-user'
    config_file.save()

    local_secret = 'local-provider-secret-should-not-leak'
    overrides_config.write_text(
        helpers.dedent(
            f'''
            [github]
            token_command = "printf {local_secret}"
            '''
        )
    )

    result = ddev('status')

    assert result.exit_code == 1, result.output
    assert 'Missing required secret: github.token' in result.output
    assert 'Code: missing-required-secret' in result.output
    assert 'Sources: command=blocked-untrusted-local-config' in result.output
    assert 'Trust workflow: run `ddev config allow`' in result.output
    assert '`ddev config deny`' in result.output
    assert local_secret not in result.output
    assert 'Traceback' not in result.output


def test_startup_command_failure_uses_stable_code_without_leaking_command(ddev, config_file, monkeypatch):
    config_file.model.github.user = 'test-user'
    command_with_secret_marker = 'printf leaked-command-should-not-appear'
    config_file.model.github.token_command = command_with_secret_marker
    config_file.save()

    def raise_non_zero(_command: str) -> str:
        raise SecretCommandError('command failed with exit code 7', reason='non_zero_exit')

    monkeypatch.setattr('ddev.config.secret_resolution.run_secret_command', raise_non_zero)

    result = ddev('status')

    assert result.exit_code == 1, result.output
    assert 'Failed to resolve required secret: github.token' in result.output
    assert 'Code: secret-command-non-zero-exit' in result.output
    assert (
        'Sources: command=configured, literal=absent, env=DD_GITHUB_TOKEN|GH_TOKEN|GITHUB_TOKEN:absent' in result.output
    )
    assert 'Run the configured *_command directly and fix its failing exit code.' in result.output
    assert command_with_secret_marker not in result.output
    assert 'Traceback' not in result.output
