# Test framework

-----

## Environments

Most integrations monitor services like databases or web servers, rather than system properties like CPU usage.
For such cases, you'll want to spin up an environment and gracefully tear it down when tests finish.

We define all environment actions in a [fixture](plugins.md#environment-manager) called `dd_environment` that
looks semantically like this:

```python
@pytest.fixture(scope='session')
def dd_environment():
    try:
        set_up_env()
        yield some_default_config
    finally:
        tear_down_env()
```

This is not only used for regular tests, but is also the basis of our [E2E testing](../e2e.md). The
[start](cli.md#start) command executes everything before the `yield` and the [stop](cli.md#stop)
command executes everything after it.

We provide a few utilities for common environment types.

### Docker

The `docker_run` utility makes it easy to create services using [docker-compose][docker-compose-docs].

```python
from datadog_checks.dev import docker_run

@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(os.path.join(HERE, 'docker', 'compose.yaml')):
        yield ...
```

Read [the reference](#datadog_checks.dev.docker.docker_run) for more information.

### Terraform

The `terraform_run` utility makes it easy to create services from a directory of [Terraform][terraform-home] files.

```python
from datadog_checks.dev.terraform import terraform_run

@pytest.fixture(scope='session')
def dd_environment():
    with terraform_run(os.path.join(HERE, 'terraform')):
        yield ...
```

Currently, we only use this for services that would be too complex to setup with Docker (like OpenStack) or
things that cannot be provided by Docker (like vSphere). We provide some ready-to-use cloud
[templates][terraform-templates-location] that are available for referencing by default. We prefer using GCP when possible.

Terraform E2E tests are not run in our public CI as that would needlessly slow down builds.

Read [the reference](#datadog_checks.dev.terraform.terraform_run) for more information.

## Mocker

The `mocker` fixture is provided by the [pytest-mock][pytest-mock-github] plugin. This fixture automatically restores
anything that was mocked at the end of each test and is more ergonomic to use than stacking decorators or nesting
context managers.

Here's an example from their docs:

```python
def test_foo(mocker):
    # all valid calls
    mocker.patch('os.remove')
    mocker.patch.object(os, 'listdir', autospec=True)
    mocked_isfile = mocker.patch('os.path.isfile')
```

It also has many other nice features, like using `pytest` introspection when comparing calls.

## Benchmarks

The `benchmark` fixture is provided by the [pytest-benchmark][pytest-benchmark-github] plugin. It enables the profiling
of functions with the low-overhead [cProfile][python-cprofile] module.

It is quite useful for seeing the approximate time a given check takes to run, as well as gaining insight into any potential
performance bottlenecks. You would use it like this:

```python
def test_large_payload(benchmark, dd_run_check):
    check = AwesomeCheck('awesome', {}, [instance])

    # Run once to get any initialization out of the way.
    dd_run_check(check)

    benchmark(dd_run_check, check)
```

To add benchmarks, define environments in `tox.ini` with `bench` somewhere in their names:

```ini
[tox]
...
envlist =
    ...
    bench

...

[testenv:bench]
```

By default, the [test](cli.md#test_1) command skips all benchmark environments and tests. To run only benchmark
environments and tests use the `--bench`/`-b` flag. The results are sorted by `tottime`, which is the total
time spent in the given function (and excluding time made in calls to sub-functions).

## Logs

We provide an easy way to utilize [log collection][integration-log-collection] with E2E [Docker environments](#docker).

1. Pass `mount_logs=True` to [docker_run](#datadog_checks.dev.docker.docker_run). This will use the logs example in
   the integration's [config spec](../meta/config_specs.md). For example, the following defines 2 example log files:

    ```yaml
    - template: logs
      example:
      - type: file
        path: /var/log/apache2/access.log
        source: apache
        service: apache
      - type: file
        path: /var/log/apache2/error.log
        source: apache
        service: apache
    ```

    ??? info "Alternatives"
        - If `mount_logs` is a sequence of `int`, only the selected indices (starting at 1) will be used. So,
          using the Apache example above, to only monitor the error log you would set it to `[2]`.
        - In lieu of a config spec, for whatever reason, you may set `mount_logs` to a `dict` containing the
          standard [logs][datadog-agent-logs] key.

1. All requested log files are available to reference as environment variables for any Docker calls as
   `DD_LOG_<LOG_CONFIG_INDEX>` where the indices start at 1.

     ```yaml
     volumes:
     - ${DD_LOG_1}:/usr/local/apache2/logs/access_log
     - ${DD_LOG_2}:/usr/local/apache2/logs/error_log
     ```

1. When [starting](cli.md#start) the environment, pass `-e DD_LOGS_ENABLED=true` to activate the Logs Agent.

## Reference

::: datadog_checks.dev.docker
    rendering:
      heading_level: 3
    selection:
      members:
        - docker_run
        - get_docker_hostname
        - get_container_ip
        - compose_file_active

::: datadog_checks.dev.terraform
    rendering:
      heading_level: 3
    selection:
      members:
        - terraform_run
