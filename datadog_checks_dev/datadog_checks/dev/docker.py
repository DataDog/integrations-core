# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os
import re
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Iterator  # noqa: F401
from urllib.parse import urlparse

from .conditions import CheckDockerLogs
from .env import environment_run, get_state, save_state
from .fs import create_file, file_exists
from .spec import load_spec
from .structures import EnvVars, LazyFunction, TempDir
from .subprocess import run_command
from .utils import find_check_root, get_current_check_name

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


CONTAINER_STABILITY_LOG_PATTERNS = (
    r'error',
    r'panic',
    r'fatal',
    r'segmentation fault',
    r'core dumped',
    r'Traceback',
)


def get_docker_hostname():
    """
    Determine the hostname Docker uses based on the environment, defaulting to `localhost`.
    """
    return urlparse(os.getenv('DOCKER_HOST', '')).hostname or 'localhost'


def get_container_ip(container_id_or_name):
    """
    Get a Docker container's IP address from its ID or name.
    """
    command = [
        'docker',
        'inspect',
        '-f',
        '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
        container_id_or_name,
    ]

    return run_command(command, capture='out', check=True).stdout.strip()


def assert_all_discovery_candidates_stable(
    dd_agent_check: Callable[..., Any],
    check_cls: type[Any],
    compose_file: str | os.PathLike[str] | None = None,
    compose_service: str | None = None,
    *,
    project_name: str | None = None,
    service_id: str | None = None,
    dd_agent_check_kwargs: Mapping[str, Any] | None = None,
    log_patterns: Sequence[str] = CONTAINER_STABILITY_LOG_PATTERNS,
) -> None:
    """Run generated discovery candidates directly and assert the target container stays stable."""
    compose_service = compose_service or _get_default_compose_service()
    container_id = _get_compose_container_id(compose_file, compose_service, project_name=project_name)
    initial_state = _inspect_container(container_id)
    previous_stdout, previous_stderr = _get_container_logs(container_id)

    ports = tuple(SimpleNamespace(number=port, name='') for port in _get_container_ports(initial_state))
    service = SimpleNamespace(
        id=service_id or compose_service,
        host=_get_container_ip_from_inspect(initial_state),
        ports=ports,
    )
    candidates = tuple(check_cls.generate_configs(service))
    if not candidates:
        raise AssertionError(f'No discovery candidates generated for service {service.id!r}')

    check_kwargs = {'check_rate': True}
    if dd_agent_check_kwargs:
        check_kwargs.update(dd_agent_check_kwargs)

    for index, candidate in enumerate(candidates, 1):
        logging.debug('Probing candidate #%d: %r', index, candidate)
        try:
            dd_agent_check(candidate, **check_kwargs)
        except Exception:
            logging.debug('Error probing candidate #%d: %r', index, candidate)
            pass

        current_container_id = _get_compose_container_id(compose_file, compose_service, project_name=project_name)
        current_state = _inspect_container(current_container_id)
        _assert_container_stable(initial_state, current_state, index)

        current_stdout, current_stderr = _get_container_logs(current_container_id)
        # Diffed separately: stdout/stderr interleaving varies across calls, breaking a combined diff.
        new_stdout = _diff_logs(previous_stdout, current_stdout)
        new_stderr = _diff_logs(previous_stderr, current_stderr)
        new_logs = new_stdout + new_stderr
        for line in new_logs.splitlines():
            logging.debug('New log line: %s', line)
        _assert_no_log_patterns(new_logs, log_patterns, index)
        previous_stdout, previous_stderr = current_stdout, current_stderr


def _get_compose_container_id(
    compose_file: str | os.PathLike[str] | None, compose_service: str, *, project_name: str | None = None
) -> str:
    compose_file = compose_file or _get_default_compose_file()
    project_name = project_name or _get_default_compose_project_name()

    command = ['docker', 'compose']
    if project_name:
        command.extend(['-p', project_name])
    command.extend(['-f', os.fspath(compose_file), 'ps', '-q', compose_service])

    container_id = run_command(command, capture='out', check=True).stdout.strip()
    if not container_id:
        raise AssertionError(f'No container found for compose service {compose_service!r}')

    return container_id


def _get_default_compose_service() -> str:
    docker_metadata = get_state('docker_compose_metadata', {})
    if docker_metadata.get('service_name'):
        return docker_metadata['service_name']

    return os.path.basename(find_check_root(depth=2))


def _get_default_compose_file() -> str:
    docker_metadata = get_state('docker_compose_metadata', {})
    if docker_metadata.get('compose_file'):
        return docker_metadata['compose_file']

    compose_file = os.path.join(find_check_root(depth=3), 'tests', 'docker', 'docker-compose.yml')
    if os.path.exists(compose_file):
        return compose_file

    raise AssertionError(
        'Could not determine the compose file. Pass compose_file explicitly or use docker_run with a compose file.'
    )


def _get_default_compose_project_name() -> str | None:
    docker_metadata = get_state('docker_compose_metadata', {})
    return docker_metadata.get('project_name') or os.getenv('COMPOSE_PROJECT_NAME')


def _inspect_container(container_id: str) -> dict[str, Any]:
    raw_inspect = run_command(['docker', 'inspect', container_id], capture='out', check=True).stdout
    return json.loads(raw_inspect)[0]


def _get_container_ip_from_inspect(inspect_data: Mapping[str, Any]) -> str:
    networks = inspect_data.get('NetworkSettings', {}).get('Networks', {})
    for network in networks.values():
        ip_address = network.get('IPAddress')
        if ip_address:
            return ip_address

    raise AssertionError(f"Could not determine container IP for {inspect_data.get('Name', '<unknown>')}")


def _get_container_ports(inspect_data: Mapping[str, Any]) -> list[int]:
    ports: set[int] = set()
    exposed_ports = inspect_data.get('Config', {}).get('ExposedPorts') or {}
    network_ports = inspect_data.get('NetworkSettings', {}).get('Ports') or {}

    for raw_port in list(exposed_ports) + list(network_ports):
        port, _, protocol = raw_port.partition('/')
        if protocol and protocol != 'tcp':
            continue
        try:
            ports.add(int(port))
        except ValueError:
            continue

    if not ports:
        raise AssertionError(f"No TCP ports found for container {inspect_data.get('Name', '<unknown>')}")

    return sorted(ports)


def _get_container_logs(container_id: str) -> tuple[str, str]:
    result = run_command(['docker', 'logs', container_id], capture=True)
    return result.stdout, result.stderr


def _diff_logs(previous: str, current: str) -> str:
    """Return the portion of `current` appended since `previous`."""
    return current[len(previous) :] if current.startswith(previous) else current


def _assert_container_stable(
    initial_state: Mapping[str, Any], current_state: Mapping[str, Any], candidate_index: int
) -> None:
    initial_id = initial_state['Id']
    current_id = current_state['Id']
    if current_id != initial_id:
        raise AssertionError(
            f'Container changed while probing candidate #{candidate_index}: {initial_id} -> {current_id}'
        )

    state = current_state.get('State', {})
    if not state.get('Running'):
        raise AssertionError(f'Container is not running after probing candidate #{candidate_index}')

    initial_restart_count = initial_state.get('RestartCount', 0)
    current_restart_count = current_state.get('RestartCount', 0)
    if current_restart_count != initial_restart_count:
        raise AssertionError(
            f'Container restart count changed while probing candidate #{candidate_index}: '
            f'{initial_restart_count} -> {current_restart_count}'
        )

    health = state.get('Health')
    if health and health.get('Status') != 'healthy':
        raise AssertionError(f"Container health is {health.get('Status')!r} after probing candidate #{candidate_index}")


def _assert_no_log_patterns(logs: str, patterns: Sequence[str], candidate_index: int) -> None:
    for pattern in patterns:
        match = re.search(pattern, logs, re.IGNORECASE)
        if match:
            raise AssertionError(
                f'Container logs matched {pattern!r} after probing candidate #{candidate_index}: {match.group(0)!r}'
            )


def get_e2e_discovery_metadata(
    check_root: str | os.PathLike[str] | None = None,
) -> dict[str, list[str]]:
    """Return Docker volume metadata for an e2e discovery run.

    Mounts the integration's ``auto_conf.yaml`` into the agent container.

    Use ``dd_agent_check_discovery`` alongside this metadata so that the static
    per-env config is temporarily replaced with an empty-instances file, leaving
    ``auto_conf.yaml`` as the sole AD template driving config-discovery.
    """
    check_root = os.fspath(check_root or find_check_root(depth=1))
    check_name = os.path.basename(check_root)
    check_pkg = os.path.join(check_root, 'datadog_checks', check_name)
    auto_conf = os.path.join(check_pkg, 'data', 'auto_conf.yaml')

    return {
        'docker_volumes': [
            f'{auto_conf}:/etc/datadog-agent/conf.d/{check_name}.d/auto_conf.yaml:ro',
            '/var/run/docker.sock:/var/run/docker.sock:ro',
        ],
    }


def compose_file_active(compose_file):
    """
    Returns a `bool` indicating whether or not a compose file has any active services.
    """
    command = ['docker', 'compose', '-f', compose_file, 'ps']
    lines = run_command(command, capture='out', check=True).stdout.strip().splitlines()

    return len(lines) > 1


def using_windows_containers():
    """
    Returns a `bool` indicating whether or not Docker is configured to use Windows containers.
    """
    os_type = run_command(['docker', 'info', '--format', '{{.OSType}}'], capture=True, check=True).stdout.strip()
    return os_type == 'windows'


@contextmanager
def shared_logs(example_log_configs, mount_whitelist=None):
    log_source = example_log_configs[0].get('source', 'check')

    if mount_whitelist is None:
        # Default to all
        mount_whitelist = range(1, len(example_log_configs) + 1)

    env_vars = {}
    docker_volumes = get_state('docker_volumes', [])

    with ExitStack() as stack:
        for i, example_log_config in enumerate(example_log_configs, 1):
            if i not in mount_whitelist:
                continue

            log_name = 'dd_log_{}'.format(i)
            d = stack.enter_context(TempDir(log_name))

            # Create the file that will ultimately be shared by containers
            shared_log_file = os.path.join(d, '{}_{}.log'.format(log_source, log_name))
            if not file_exists(shared_log_file):
                create_file(shared_log_file)

            # Set config to the path in the Agent
            agent_mount_path = '/var/log/{}/{}'.format(log_source, log_name)
            example_log_config['path'] = agent_mount_path
            docker_volumes.append('{}:{}'.format(shared_log_file, agent_mount_path))

            # If service is the default, use the source
            if example_log_config.get('service', '<SERVICE>') == '<SERVICE>':
                example_log_config['service'] = log_source

            # Make it available to reference for Docker volumes
            env_vars[log_name.upper()] = shared_log_file

        # Inject and persist this data for `env test` & `env stop`
        save_state('logs_config', example_log_configs)
        save_state('docker_volumes', docker_volumes)

        with EnvVars(env_vars):
            yield


@contextmanager
def docker_run(
    compose_file=None,
    wait_for_health=True,
    build=False,
    service_name=None,
    up=None,
    down=None,
    on_error=None,
    sleep=None,
    endpoints=None,
    log_patterns=None,
    mount_logs=False,
    conditions=None,
    env_vars=None,
    wrappers=None,
    attempts=None,
    attempts_wait=1,
    capture=None,
):
    """
    A convenient context manager for safely setting up and tearing down Docker environments.

    Parameters:

        compose_file (str):
            A path to a Docker compose file. A custom tear
            down is not required when using this.
        wait_for_health (bool):
            Whether or not to wait for the health of the service to be healthy before yielding.
        build (bool):
            Whether or not to build images for when `compose_file` is provided
        service_name (str):
            Optional name for when ``compose_file`` is provided
        up (callable):
            A custom setup callable
        down (callable):
            A custom tear down callable. This is required when using a custom setup.
        on_error (callable):
            A callable called in case of an unhandled exception
        sleep (float):
            Number of seconds to wait before yielding. This occurs after all conditions are successful.
        endpoints (list[str]):
            Endpoints to verify access for before yielding. Shorthand for adding
            `CheckEndpoints(endpoints)` to the `conditions` argument.
        log_patterns (list[str | re.Pattern]):
            Regular expression patterns to find in Docker logs before yielding.
            This is only available when `compose_file` is provided. Shorthand for adding
            `CheckDockerLogs(compose_file, log_patterns, 'all')` to the `conditions` argument.
        mount_logs (bool):
            Whether or not to mount log files in Agent containers based on example logs configuration
        conditions (callable):
            A list of callable objects that will be executed before yielding to check for errors
        env_vars (dict[str, str]):
            A dictionary to update `os.environ` with during execution. When `compose_file` is provided and
            `COMPOSE_PROJECT_NAME` isn't set here, already in `os.environ`, or saved from a previous E2E
            start run, it defaults to the check's directory name so that concurrent E2E runs sharing a
            Docker daemon don't collide on Compose's own directory-basename-derived default project name.
        wrappers (list[callable]):
            A list of context managers to use during execution
        attempts (int):
            Number of attempts to run `up` and the `conditions` successfully. Defaults to 2 in CI
        attempts_wait (int):
            Time to wait between attempts
    """
    if compose_file and up:
        raise TypeError('You must select either a compose file or a custom setup callable, not both.')

    if compose_file is not None:
        if not isinstance(compose_file, str):
            raise TypeError('The path to the compose file is not a string: {}'.format(repr(compose_file)))

        env_vars = dict(env_vars) if env_vars else {}
        if not env_vars.get('COMPOSE_PROJECT_NAME') and not os.getenv('COMPOSE_PROJECT_NAME'):
            docker_metadata = get_state('docker_compose_metadata', {})
            # An extra level deep because of the context manager
            env_vars['COMPOSE_PROJECT_NAME'] = docker_metadata.get('project_name') or get_current_check_name(depth=2)

        composeFileArgs = {'compose_file': compose_file, 'build': build, 'service_name': service_name}
        if capture is not None:
            composeFileArgs['capture'] = capture
        composeFileArgs['wait_for_health'] = wait_for_health
        set_up = ComposeFileUp(**composeFileArgs)
        if down is not None:
            tear_down = down
        else:
            tear_down = ComposeFileDown(compose_file)
        if on_error is None:
            on_error = ComposeFileLogs(compose_file)
    else:
        set_up = up
        tear_down = down

    docker_conditions = []

    if log_patterns is not None:
        if compose_file is None:
            raise ValueError(
                'The `log_patterns` convenience is unavailable when using '
                'a custom setup. Please use a custom condition instead.'
            )
        docker_conditions.append(CheckDockerLogs(compose_file, log_patterns, 'all'))

    if conditions is not None:
        docker_conditions.extend(conditions)

    wrappers = list(wrappers) if wrappers is not None else []

    if mount_logs:
        if isinstance(mount_logs, dict):
            wrappers.append(shared_logs(mount_logs['logs']))
        # Easy mode, read example config
        else:
            # An extra level deep because of the context manager
            check_root = find_check_root(depth=2)

            example_log_configs = _read_example_logs_config(check_root)
            if mount_logs is True:
                wrappers.append(shared_logs(example_log_configs))
            elif isinstance(mount_logs, (list, set)):
                wrappers.append(shared_logs(example_log_configs, mount_whitelist=mount_logs))
            else:
                raise TypeError(
                    'mount_logs: expected True, a list or a set, but got {}'.format(type(mount_logs).__name__)
                )

    if compose_file is not None:
        save_state(
            'docker_compose_metadata',
            {
                'compose_file': compose_file,
                'project_name': env_vars.get('COMPOSE_PROJECT_NAME') or os.getenv('COMPOSE_PROJECT_NAME'),
                'service_name': service_name,
            },
        )

    with environment_run(
        up=set_up,
        down=tear_down,
        on_error=on_error,
        sleep=sleep,
        endpoints=endpoints,
        conditions=docker_conditions,
        env_vars=env_vars,
        wrappers=wrappers,
        attempts=attempts,
        attempts_wait=attempts_wait,
    ) as result:
        yield result


class ComposeFileUp(LazyFunction):
    def __init__(
        self,
        compose_file: str,
        build: bool = False,
        service_name: str | None = None,
        capture: str | None = None,
        wait_for_health: bool = True,
    ):
        self.compose_file = compose_file
        self.build = build
        self.service_name = service_name
        self.capture = capture
        self.wait_for_health = wait_for_health
        self.command = ['docker', 'compose', '-f', self.compose_file, 'up', '-d', '--force-recreate']

        if wait_for_health:
            self.command.append('--wait')

        if self.build:
            self.command.append('--build')

        if self.service_name:
            self.command.append(self.service_name)

    def __call__(self):
        args = {'check': True}
        if self.capture is not None:
            args['capture'] = self.capture
        return run_command(self.command, **args)


class ComposeFileLogs(LazyFunction):
    def __init__(self, compose_file, check=True):
        self.compose_file = compose_file
        self.check = check
        self.command = ['docker', 'compose', '-f', self.compose_file, 'logs']

    def __call__(self, exception):
        return run_command(self.command, capture=False, check=self.check)


class ComposeFileDown(LazyFunction):
    def __init__(self, compose_file, check=True):
        self.compose_file = compose_file
        self.check = check
        self.command = [
            'docker',
            'compose',
            '-f',
            self.compose_file,
            'down',
            '--volumes',
            '--remove-orphans',
            '-t',
            '0',
        ]

    def __call__(self):
        return run_command(self.command, check=self.check)


def _read_example_logs_config(check_root):
    spec = load_spec(check_root)

    for f in spec['files']:
        for option in f['options']:
            if option.get('template') == 'logs':
                return option['example']

    raise ValueError('No logs example found')


@contextmanager
def temporarily_stop_service(service, compose_file, check=True):
    # type: (str, str, bool) -> Iterator[None]
    stop_command = ['docker', 'compose', '-f', compose_file, 'stop', service]
    start_command = ['docker', 'compose', '-f', compose_file, 'start', service]

    run_command(stop_command, capture=False, check=check)
    yield
    run_command(start_command, capture=False, check=check)
