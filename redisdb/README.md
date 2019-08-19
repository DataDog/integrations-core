# Redis Integration

## Overview

Whether you use Redis as a database, cache, or message queue, this integration helps you track problems with your Redis servers and the parts of your infrastructure that they serve. The Datadog Agent's Redis check collects metrics related to performance, memory usage, blocked clients, slave connections, disk persistence, expired and evicted keys, and many more.

## Setup
### Installation

The Redis check is included in the [Datadog Agent][2] package, so you don't need to install anything else on your Redis servers.

### Configuration
#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

##### Metric collection

1. Edit the `redisdb.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. The following parameters may require updating. See the [sample redisdb.d/conf.yaml][4] for all available configuration options.

    ```yaml
      init_config:
      instances:
        ## @param host - string - required
        ## Enter the host to connect to.
        - host: localhost
          ## @param port - integer - required
          ## Enter the port of the host to connect to.
          port: 6379
      ```

2. [Restart the Agent][5].

##### Log collection

**Available for Agent >6.0**

1. Collecting logs is disabled by default in the Datadog Agent, enable it in your `datadog.yaml` file:

    ```yaml
      logs_enabled: true
    ```

2. Uncomment and edit this configuration block at the bottom of your `redisdb.d/conf.yaml`:

    ```yaml
      logs:
          - type: file
            path: /var/log/redis_6379.log
            source: redis
            sourcecategory: database
            service: myapplication
    ```

    Change the `path` and `service` parameter values and configure them for your environment. See the [sample redisdb.yaml][4] for all available configuration options.

3. [Restart the Agent][5].

#### Containerized
For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying the parameters below.

##### Metric collection

`<INTEGRATION_NAME>`<br>
The name for this integration is `redisdb`.

`<INIT_CONFIG>`<br>
The configuration for this integration's `init_config` section is blank or `{}`.

`<INSTANCE_CONFIG>`<br>
The configuration for this integration's `instances` section is:
```text
{"host": "%%host%%","port":"6379","password":"%%env_REDIS_PASSWORD%%"}
```

##### Log collection

**Available for Agent v6.5+**

Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Docker log collection][11].

`<LOG_CONFIG>`<br>
The configuration for this integration's `logs` section is:
```text
{"source": "redis", "service": "<YOUR_APP_NAME>"}
```

### Validation

[Run the Agent's status subcommand][6] and look for `redisdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The Redis check does not include any events.

### Service Checks

**redis.can_connect**:<br>
Returns `CRITICAL` if the Agent cannot connect to Redis to collect metrics, otherwise returns `OK`.

**redis.replication.master_link_status**:<br>
Returns `CRITICAL` if this Redis instance is unable to connect to its master instance, otherwise returns `OK`.

## Troubleshooting

* [Redis Integration Error: "unknown command 'CONFIG'"][8]

### Agent cannot connect

```
    redisdb
    -------
      - instance #0 [ERROR]: 'Error 111 connecting to localhost:6379. Connection refused.'
      - Collected 0 metrics, 0 events & 1 service chec
```

Check that the connection info in `redisdb.yaml` is correct.

### Agent cannot authenticate

```
    redisdb
    -------
      - instance #0 [ERROR]: 'NOAUTH Authentication required.'
      - Collected 0 metrics, 0 events & 1 service check
```

Configure a `password` in `redisdb.yaml`.

## Development

See the [main documentation][9] for more details about how to test and develop Agent based integrations.

### Testing Guidelines

This check has 2 test matrix, one detailing the test type:

* unit tests (no need for a Redis instance running)
* integration tests (a Redis instance must run locally)

another matrix defines the Redis versions to be used with integration tests:

* redis 3.2
* redis 4.0

The first matrix is handled by pytest using `mark`: tests that need a running redis instance must be decorated like this:

```python
@pytest.mark.integration
def test_something_requiring_redis_running():
  pass
```

Running the tests with `pytest -m"integration"` will run *only* integration tests while `pytest -m"not integration"` will run whatever was not marked as an integration test.

The second matrix is defined with `tox` like this:

```ini
envlist = unit, redis{32,40}, flake8

...

[testenv:redis32]
setenv = REDIS_VERSION=3.2
...

[testenv:redis40]
setenv = REDIS_VERSION=4.0
...
```

#### Integration tests

Redis instances are orchestrated with `docker-compose` which is now a dependency
to run the integration tests. It's `pytest` responsible to start/stop/dispose an
instance using the `fixture` concept.

This is how a fixture orchestrating Redis instances looks like:

```python
@pytest.fixture(scope="session")
def redis_auth():
    # omitted docker-compose invokation setup here ...
    subprocess.check_call(args + ["up", "-d"], env=env)
    yield
    subprocess.check_call(args + ["down"], env=env)
```

the basic concept is that `docker-compose up` is run right after the fixture
is made available to the test function (it blocks on `yield`). When the test
has done, `yield` unblocks and `docker-compose down` is called. Notice the
`scope=session` argument passed to the fixture decorator, it allows the
`yield` to block only once for **all the tests** , unblocking only after the
last test: this is useful to avoid having `docker-compose up` and `down`
called at every test. One caveat with this approach is that if you have data
in Redis, some test might operate on a dirty database - this is not an issue
in this case but something to keep in mind when using `scope=session`.

#### Running the tests locally

**Note**: you need `docker` and `docker-compose` to be installed on your system
in order to run the tests locally.

During development, tests can be locally run with tox, same as in the CI. In the case of Redis, there might be no need to test the whole matrix all the times, so for example if you want to run only the unit/mocked tests:

```shell
tox -e unit
```

if you want to run integration tests but against one Redis version only:

```shell
tox -e redis40
```

tox is great because it creates a virtual Python environment for each tox env but if you don't need this level of isolation you can speed up the development iterations using `pytest` directly (which is what tox does under the hood):

```shell
REDIS_VERSION=4.0 pytest
```

or if you don't want to run integration tests:

```shell
pytest -m"not integration"
```

## Further Reading

Additional helpful documentation, links, and articles:

* [How to monitor Redis performance metrics][10]


[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/redisdb/datadog_checks/redisdb/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/?tab=agentv6#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/redisdb/metadata.csv
[8]: https://docs.datadoghq.com/integrations/faq/redis-integration-error-unknown-command-config
[9]: https://docs.datadoghq.com/developers/integrations
[10]: https://www.datadoghq.com/blog/how-to-monitor-redis-performance-metrics
[11]: https://docs.datadoghq.com/agent/docker/log/?tab=containerinstallation#setup
