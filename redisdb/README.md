# Redis Integration

## Overview

Whether you use Redis as a database, cache, or message queue, this integration helps you track problems with your Redis servers and the parts of your infrastructure that they serve. The Datadog Agent's Redis check collects a wealth of metrics related to performance, memory usage, blocked clients, slave connections, disk persistence, expired and evicted keys, and many more.

## Setup

### Installation

The Redis check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Redis servers.

### Configuration

Edit the `redisdb.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][9] to start collecting your Redis [metrics](#metric-collection) and [logs](#log-collection).
See the [sample redis.d/conf.yaml][2] for all available configuration options.

#### Metric Collection

Add this configuration block to your `redisdb.d/conf.yaml` file to start gathering your [Redis metrics](#metrics):

```
init_config:

instances:
  - host: localhost
    port: 6379 # or wherever your Redis listens
  # unix_socket_path: /var/run/redis/redis.sock # if your Redis uses a socket instead of TCP
  # password: myredispassword                   # if your Redis requires auth
```

Configuration Options:

* `unix_socket_path` - (Optional) - Can be used instead of `host` and `port`.
* `db`, `password`, and `socket_timeout` - (Optional) - Additional connection options.
* `warn_on_missing_keys` - (Optional) - Display a warning in the info page if the keys we're tracking are missing.
* `slowlog-max-len` - (Optional) - Maximum number of entries to fetch from the slow query log. By default, the check will
        read this value from the Redis config. If it's above 128, it will default to 128 due to potential increased latency
        to retrieve more than 128 slowlog entries every 15 seconds. If you need to get more entries from the slow query logs
        set the value here. Warning: It may impact the performance of your Redis instance
* `command_stats` - (Optional) - Collect INFO COMMANDSTATS output as metrics.

See the [sample redisdb.d/conf.yaml][2] for all available configuration options.

[Restart the Agent][3] to begin sending Redis metrics to Datadog.

#### Log Collection

**Available for Agent >6.0**

* Collecting logs is disabled by default in the Datadog Agent, you need to enable it in `datadog.yaml`:

  ```
  logs_enabled: true
  ```

* Add this configuration block to your `redisdb.d/conf.yaml` file to start collecting your Redis Logs:

  ```
    logs:
        - type: file
          path: /var/log/redis_6379.log
          source: redis
          sourcecategory: database
          service: myapplication
  ```

  Change the `path` and `service` parameter values and configure them for your environment.
  See the [sample redisdb.yaml][2] for all available configuration options.

* [Restart the Agent][3] to begin sending Redis logs to Datadog.

### Validation

[Run the Agent's `status` subcommand][4] and look for `redisdb` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][5] for a list of metrics provided by this integration.

### Events

The Redis check does not include any events at this time.

### Service Checks

**redis.can_connect**:

Returns CRITICAL if the Agent cannot connect to Redis to collect metrics, otherwise OK.

**redis.replication.master_link_status**

Returns `CRITICAL` if this Redis instance is unable to connect to its master instance. Returns `OK` otherwise.

## Troubleshooting

* [Redis Integration Error: "unknown command 'CONFIG'"][6]

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

Please refer to the [main documentation][7] for more details about how to test and develop Agent based integrations.

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

Read our [series of blog posts][8] about how to monitor your Redis servers with Datadog. We detail the key performance metrics, how to collect them, and how to use Datadog to monitor Redis.


[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/redisdb/datadog_checks/redisdb/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/redisdb/metadata.csv
[6]: https://docs.datadoghq.com/integrations/faq/redis-integration-error-unknown-command-config
[7]: https://docs.datadoghq.com/developers/integrations/
[8]: https://www.datadoghq.com/blog/how-to-monitor-redis-performance-metrics/
[9]: https://docs.datadoghq.com/agent/faq/agent-configuration-files/#agent-configuration-directory
