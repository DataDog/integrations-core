# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os
from contextlib import contextmanager

import mock
import pytest
import tenacity

from datadog_checks.dev._env import get_state, serialize_data
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.dev.docker import (
    ComposeFileUp,
    _get_compose_container_id,
    assert_all_discovery_candidates_stable,
    compose_file_active,
    docker_run,
)
from datadog_checks.dev.subprocess import run_command

from .common import not_windows_ci

pytestmark = [not_windows_ci]
HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


def _docker_result(stdout='', stderr='', code=0):
    return mock.Mock(stdout=stdout, stderr=stderr, code=code)


def _container_inspect(*, restart_count=0, running=True, health='healthy', ports=None):
    ports = ports or ('8080/tcp', '9090/tcp')
    state = {'Running': running}
    if health is not None:
        state['Health'] = {'Status': health}

    return {
        'Id': 'container-id',
        'Name': '/service',
        'Config': {'ExposedPorts': {port: {} for port in ports}},
        'NetworkSettings': {
            'Networks': {'default': {'IPAddress': '172.18.0.2'}},
            'Ports': dict.fromkeys(ports),
        },
        'RestartCount': restart_count,
        'State': state,
    }


class TestComposeFileActive:
    def test_down(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')
        run_command(['docker', 'compose', '-f', compose_file, 'down'], capture=True)

        assert compose_file_active(compose_file) is False

    def test_up(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        try:
            run_command(['docker', 'compose', '-f', compose_file, 'up', '-d'], check=True)
            assert compose_file_active(compose_file) is True
        finally:
            run_command(['docker', 'compose', '-f', compose_file, 'down'], capture=True)


class TestDockerRun:
    def test_wait_for_health_default(self):
        set_up = self.get_set_up()

        assert '--wait' in set_up.command

    def test_wait_for_health_explicit_disable(self):
        set_up = self.get_set_up(wait_for_health=False)

        assert '--wait' not in set_up.command

    def test_wait_for_health_typo_rejected(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        with pytest.raises(TypeError, match='unexpected keyword argument'):
            with docker_run(compose_file, waith_for_health=False):
                pass

    def get_set_up(self, **kwargs):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        with mock.patch('datadog_checks.dev.docker.environment_run') as environment_run:
            environment_run.return_value.__enter__.return_value = None
            with docker_run(compose_file, **kwargs):
                pass

        return environment_run.call_args[1]['up']

    @pytest.mark.parametrize(
        "capture",
        [
            None,
            True,
        ],
    )
    def test_compose_file(self, capture):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        try:
            args = {}
            if capture is not None:
                args['capture'] = capture
            with docker_run(compose_file, **args):
                assert compose_file_active(compose_file) is True
            assert compose_file_active(compose_file) is False
        finally:
            run_command(['docker', 'compose', '-f', compose_file, 'down'], capture=True)

    @pytest.mark.parametrize(
        "attempts,expected_call_count",
        [
            (None, 1),
            (0, 1),
            (1, 1),
            (3, 3),
        ],
    )
    def test_retry_on_failed_conditions(self, attempts, expected_call_count):
        condition = mock.MagicMock()
        condition.side_effect = Exception("exception")

        expected_exception = tenacity.RetryError
        if attempts is None:
            if running_on_ci():
                expected_call_count = 2
            else:
                expected_exception = Exception

        with pytest.raises(expected_exception):
            with docker_run(
                up=mock.MagicMock(), down=mock.MagicMock(), attempts=attempts, conditions=[condition], attempts_wait=0
            ):
                pass

        assert condition.call_count == expected_call_count

    def test_retry_condition_failed_only_on_first_run(self):
        up = mock.MagicMock()
        up.return_value = ""

        condition = mock.MagicMock()
        condition.side_effect = [Exception("exception"), None, None]

        with docker_run(up=up, down=mock.MagicMock(), attempts=3, conditions=[condition], attempts_wait=0):
            assert condition.call_count == 2


class TestComposeFileUp:
    def test_wait_for_health_default(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        compose_file_up = ComposeFileUp(compose_file)

        assert '--wait' in compose_file_up.command

    def test_wait_for_health_explicit_disable(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        compose_file_up = ComposeFileUp(compose_file, wait_for_health=False)

        assert '--wait' not in compose_file_up.command

    def test_wait_for_health_typo_rejected(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        with pytest.raises(TypeError, match='unexpected keyword argument'):
            ComposeFileUp(compose_file, waith_for_health=False)


def test_assert_all_discovery_candidates_stable_generates_and_runs_candidates():
    class DiscoveryCheck:
        service = None

        @classmethod
        def generate_configs(cls, service):
            cls.service = service
            for port in service.ports:
                yield {'init_config': {}, 'instances': [{'url': f'http://{service.host}:{port.number}/metrics'}]}

    inspect_data = _container_inspect(ports=('8080/tcp', '9090/tcp'))
    logs = iter(
        [
            _docker_result(stdout='ready\n'),
            _docker_result(stdout='ready\n'),
            _docker_result(stdout='ready\n'),
        ]
    )

    def fake_run_command(command, **kwargs):
        if command[:2] == ['docker', 'ps']:
            return _docker_result(stdout='container-id\n')
        if command[:2] == ['docker', 'inspect']:
            return _docker_result(stdout=json.dumps([inspect_data]))
        if command[:2] == ['docker', 'logs']:
            return next(logs)
        raise AssertionError(f'Unexpected command: {command}')

    dd_agent_check = mock.Mock(side_effect=[ValueError('expected failure'), None])

    with mock.patch('datadog_checks.dev.docker.run_command', side_effect=fake_run_command):
        assert_all_discovery_candidates_stable(
            dd_agent_check,
            DiscoveryCheck,
            '/tmp/docker-compose.yml',
            'service',
            project_name='project',
        )

    assert DiscoveryCheck.service.id == 'service'
    assert DiscoveryCheck.service.host == '172.18.0.2'
    assert [port.number for port in DiscoveryCheck.service.ports] == [8080, 9090]
    assert dd_agent_check.call_args_list == [
        mock.call({'init_config': {}, 'instances': [{'url': 'http://172.18.0.2:8080/metrics'}]}, check_rate=True),
        mock.call({'init_config': {}, 'instances': [{'url': 'http://172.18.0.2:9090/metrics'}]}, check_rate=True),
    ]


def test_assert_all_discovery_candidates_stable_uses_docker_run_metadata():
    class DiscoveryCheck:
        service = None

        @classmethod
        def generate_configs(cls, service):
            cls.service = service
            yield {'init_config': {}, 'instances': [{'url': f'http://{service.host}:8080/metrics'}]}

    commands = []

    def fake_run_command(command, **kwargs):
        commands.append(command)
        if command[:2] == ['docker', 'ps']:
            return _docker_result(stdout='container-id\n')
        if command[:2] == ['docker', 'inspect']:
            return _docker_result(stdout=json.dumps([_container_inspect(ports=('8080/tcp',))]))
        if command[:2] == ['docker', 'logs']:
            return _docker_result(stdout='ready\n')
        raise AssertionError(f'Unexpected command: {command}')

    docker_metadata = {'compose_file': '/tmp/docker-compose.yml', 'project_name': 'project', 'service_name': 'service'}

    with mock.patch('datadog_checks.dev.docker.get_state', return_value=docker_metadata):
        with mock.patch('datadog_checks.dev.docker.run_command', side_effect=fake_run_command):
            assert_all_discovery_candidates_stable(mock.Mock(), DiscoveryCheck)

    assert commands[0] == [
        'docker',
        'ps',
        '--quiet',
        '--filter',
        'label=com.docker.compose.project=project',
        '--filter',
        'label=com.docker.compose.service=service',
        '--filter',
        'label=com.docker.compose.oneoff=False',
    ]
    assert DiscoveryCheck.service.id == 'service'


def test_get_compose_container_id_falls_back_to_compose_file_without_project_metadata():
    with mock.patch('datadog_checks.dev.docker.get_state', return_value={}):
        with mock.patch(
            'datadog_checks.dev.docker.run_command', return_value=_docker_result(stdout='container-id\n')
        ) as run:
            container_id = _get_compose_container_id('/tmp/docker-compose.yml', 'service')

    assert container_id == 'container-id'
    run.assert_called_once_with(
        ['docker', 'compose', '-f', '/tmp/docker-compose.yml', 'ps', '-q', 'service'],
        capture='out',
        check=True,
    )


def test_docker_run_saves_compose_metadata(monkeypatch):
    @contextmanager
    def fake_environment_run(**kwargs):
        yield None

    monkeypatch.delenv('DDEV_E2E_ENV_docker_compose_metadata', raising=False)

    with mock.patch('datadog_checks.dev.docker.environment_run', fake_environment_run):
        with docker_run(
            '/tmp/docker-compose.yml',
            env_vars={'COMPOSE_PROJECT_NAME': 'project'},
            service_name='service',
        ):
            pass

    assert os.environ['DDEV_E2E_ENV_docker_compose_metadata']


@pytest.fixture
def captured_env_vars():
    captured = {}

    @contextmanager
    def fake_environment_run(**kwargs):
        captured.update(kwargs['env_vars'])
        yield None

    with mock.patch('datadog_checks.dev.docker.environment_run', fake_environment_run):
        yield captured


def test_docker_run_defaults_compose_project_name(monkeypatch, captured_env_vars):
    monkeypatch.delenv('COMPOSE_PROJECT_NAME', raising=False)
    monkeypatch.delenv('DDEV_E2E_ENV_docker_compose_metadata', raising=False)

    with docker_run('/tmp/docker-compose.yml', service_name='service'):
        pass

    assert captured_env_vars['COMPOSE_PROJECT_NAME'] == 'datadog_checks_dev'
    assert get_state('docker_compose_metadata')['project_name'] == 'datadog_checks_dev'


def test_docker_run_respects_explicit_compose_project_name(monkeypatch, captured_env_vars):
    monkeypatch.delenv('COMPOSE_PROJECT_NAME', raising=False)

    with docker_run(
        '/tmp/docker-compose.yml',
        env_vars={'COMPOSE_PROJECT_NAME': 'custom'},
        service_name='service',
    ):
        pass

    assert captured_env_vars['COMPOSE_PROJECT_NAME'] == 'custom'


def test_docker_run_respects_compose_project_name_env_var(monkeypatch, captured_env_vars):
    monkeypatch.setenv('COMPOSE_PROJECT_NAME', 'from_environ')
    monkeypatch.delenv('DDEV_E2E_ENV_docker_compose_metadata', raising=False)

    with docker_run('/tmp/docker-compose.yml', service_name='service'):
        pass

    assert 'COMPOSE_PROJECT_NAME' not in captured_env_vars
    assert get_state('docker_compose_metadata')['project_name'] == 'from_environ'


def test_docker_run_reuses_saved_compose_project_name(monkeypatch, captured_env_vars):
    monkeypatch.delenv('COMPOSE_PROJECT_NAME', raising=False)
    monkeypatch.setenv(
        'DDEV_E2E_ENV_docker_compose_metadata',
        serialize_data(
            {'compose_file': '/tmp/docker-compose.yml', 'project_name': 'saved_project', 'service_name': 'service'}
        ),
    )

    with docker_run('/tmp/docker-compose.yml', service_name='service'):
        pass

    assert captured_env_vars['COMPOSE_PROJECT_NAME'] == 'saved_project'
    assert get_state('docker_compose_metadata')['project_name'] == 'saved_project'


def test_assert_all_discovery_candidates_stable_reports_incremental_logs(caplog):
    class DiscoveryCheck:
        @classmethod
        def generate_configs(cls, service):
            yield {'init_config': {}, 'instances': [{'url': f'http://{service.host}:8080/metrics'}]}
            yield {'init_config': {}, 'instances': [{'url': f'http://{service.host}:9090/metrics'}]}

    logs = iter(
        [
            _docker_result(stdout='ready\n'),
            _docker_result(stdout='ready\nfirst\n'),
            _docker_result(stdout='ready\nfirst\nsecond\n'),
        ]
    )

    def fake_run_command(command, **kwargs):
        if command[:2] == ['docker', 'ps']:
            return _docker_result(stdout='container-id\n')
        if command[:2] == ['docker', 'inspect']:
            return _docker_result(stdout=json.dumps([_container_inspect()]))
        if command[:2] == ['docker', 'logs']:
            return next(logs)
        raise AssertionError(f'Unexpected command: {command}')

    with mock.patch('datadog_checks.dev.docker.run_command', side_effect=fake_run_command):
        with caplog.at_level(logging.DEBUG):
            assert_all_discovery_candidates_stable(
                mock.Mock(),
                DiscoveryCheck,
                '/tmp/docker-compose.yml',
                'service',
                project_name='project',
            )

    assert [record.message for record in caplog.records if record.message.startswith('New log line:')] == [
        'New log line: first',
        'New log line: second',
    ]


def test_assert_all_discovery_candidates_stable_detects_restarts():
    class DiscoveryCheck:
        @classmethod
        def generate_configs(cls, service):
            yield {'init_config': {}, 'instances': [{'url': f'http://{service.host}:8080/metrics'}]}

    inspect_results = iter(
        [
            _container_inspect(restart_count=0),
            _container_inspect(restart_count=1),
        ]
    )

    def fake_run_command(command, **kwargs):
        if command[:2] == ['docker', 'ps']:
            return _docker_result(stdout='container-id\n')
        if command[:2] == ['docker', 'inspect']:
            return _docker_result(stdout=json.dumps([next(inspect_results)]))
        if command[:2] == ['docker', 'logs']:
            return _docker_result(stdout='ready\n')
        raise AssertionError(f'Unexpected command: {command}')

    with mock.patch('datadog_checks.dev.docker.run_command', side_effect=fake_run_command):
        with pytest.raises(AssertionError, match='restart count changed'):
            assert_all_discovery_candidates_stable(
                mock.Mock(),
                DiscoveryCheck,
                '/tmp/docker-compose.yml',
                'service',
                project_name='project',
            )


def test_assert_all_discovery_candidates_stable_detects_new_crash_logs():
    class DiscoveryCheck:
        @classmethod
        def generate_configs(cls, service):
            yield {'init_config': {}, 'instances': [{'url': f'http://{service.host}:8080/metrics'}]}

    logs = iter(
        [
            _docker_result(stdout='ready\n'),
            _docker_result(stdout='ready\npanic: boom\n'),
        ]
    )

    def fake_run_command(command, **kwargs):
        if command[:2] == ['docker', 'ps']:
            return _docker_result(stdout='container-id\n')
        if command[:2] == ['docker', 'inspect']:
            return _docker_result(stdout=json.dumps([_container_inspect()]))
        if command[:2] == ['docker', 'logs']:
            return next(logs)
        raise AssertionError(f'Unexpected command: {command}')

    with mock.patch('datadog_checks.dev.docker.run_command', side_effect=fake_run_command):
        with pytest.raises(AssertionError, match='Container logs matched'):
            assert_all_discovery_candidates_stable(
                mock.Mock(),
                DiscoveryCheck,
                '/tmp/docker-compose.yml',
                'service',
                project_name='project',
            )


def test_assert_all_discovery_candidates_stable_ignores_old_stderr_when_new_stdout_arrives():
    # Regression test: new stdout previously shifted unchanged stderr, replaying it as new.
    class DiscoveryCheck:
        @classmethod
        def generate_configs(cls, service):
            yield {'init_config': {}, 'instances': [{'url': f'http://{service.host}:8080/metrics'}]}

    logs = iter(
        [
            _docker_result(stdout='', stderr='old startup error\n'),
            _docker_result(stdout='new access log line\n', stderr='old startup error\n'),
        ]
    )

    def fake_run_command(command, **kwargs):
        if command[:2] == ['docker', 'ps']:
            return _docker_result(stdout='container-id\n')
        if command[:2] == ['docker', 'inspect']:
            return _docker_result(stdout=json.dumps([_container_inspect()]))
        if command[:2] == ['docker', 'logs']:
            return next(logs)
        raise AssertionError(f'Unexpected command: {command}')

    with mock.patch('datadog_checks.dev.docker.run_command', side_effect=fake_run_command):
        assert_all_discovery_candidates_stable(
            mock.Mock(),
            DiscoveryCheck,
            '/tmp/docker-compose.yml',
            'service',
            project_name='project',
        )
