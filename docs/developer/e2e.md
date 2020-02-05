# E2E

-----

Any integration that makes use of our [pytest plugin](ddev/plugins.md#pytest) in its test suite supports
end-to-end testing on a live [Datadog Agent](https://docs.datadoghq.com/agent/).

The entrypoint for E2E management is the command group `ddev env`.

## Discovery

Use the `ls` command to see what environments are available, for example:

```
$ ddev env ls envoy
envoy:
    py27
    py38
```

You'll notice that only environments that actually run tests are available.

Running simply `ddev env ls` with no arguments will display the active environments.

## Creation

To start an environment run `ddev env start <INTEGRATION> <ENVIRONMENT>`, for example:

```
$ ddev env start envoy py38
Setting up environment `py38`... success!
Updating `datadog/agent-dev:master`... success!
Detecting the major version... Agent 7 detected
Writing configuration for `py38`... success!
Starting the Agent... success!

Config file (copied to your clipboard): C:\Users\ofek\AppData\Local\dd-checks-dev\envs\envoy\py38\config\envoy.yaml
To run this check, do: ddev env check envoy py38
To stop this check, do: ddev env stop envoy py38
```

This sets up the selected environment and an instance of the Agent running in a Docker container. The default
configuration is defined by each environment's test suite and is saved to a file, which is then mounted to the
Agent container so you may freely modify it.

Let's see what we have running:

```
$ docker ps --format "table {{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Names}}"
IMAGE                          STATUS                            PORTS                                                     NAMES
datadog/agent-dev:master-py3   Up 4 seconds (health: starting)                                                             dd_envoy_py38
default_service2               Up 5 seconds                      80/tcp, 10000/tcp                                         default_service2_1
envoyproxy/envoy:latest        Up 5 seconds                      0.0.0.0:8001->8001/tcp, 10000/tcp, 0.0.0.0:8000->80/tcp   default_front-envoy_1
default_xds                    Up 5 seconds                      8080/tcp                                                  default_xds_1
default_service1               Up 5 seconds                      80/tcp, 10000/tcp                                         default_service1_1
```

### Agent version

You can select a particular build of the Agent to use with the `--agent`/`-a` option. Any Docker image is valid e.g. `datadog/agent:7.17.0`.

A custom nightly build will be used by default, which is re-built on every commit to the [Datadog Agent repository](https://github.com/DataDog/datadog-agent).

### Integration version

By default the version of the integration used will be the one shipped with the chosen Agent version, as if you had passed in the `--prod` flag. If you wish
to modify an integration and test changes in real time, use the `--dev` flag.

Doing so will mount and install the integration in the Agent container. All modifications to the integration's directory will be propagated to the Agent,
whether it be a code change or switching to a different Git branch.

If you modify the [base package](base/about.md) then you will need to mount that with the `--base` flag, which implicitly activates `--dev`.

## Testing

To run tests against the live Agent, use the `ddev env test` command. It is similar to the [test command](testing.md#usage) except
it is capable of running tests [marked as E2E](ddev/plugins.md#agent-check-runner), and only runs such tests.

### Automation

You can use the `--new-env`/`-ne` flag to automate environment management. For example running:

```
ddev env test apache:py38 vault:py38 -ne
```

will start the `py38` environment for Apache, run E2E tests, tear down the environment, and then do the same for Vault.

!!! tip
    Since running tests implies code changes are being introduced, `--new-env` enables `--dev` by default.

## Execution

Similar to the Agent's `check` command, you can perform manual check runs using `ddev env check <INTEGRATION> <ENVIRONMENT>`, for example:

```
$ ddev env check envoy py38 --log-level debug
...
=========
Collector
=========

  Running Checks
  ==============

    envoy (1.12.0)
    --------------
      Instance ID: envoy:c705bd922a3c275c [OK]
      Configuration Source: file:/etc/datadog-agent/conf.d/envoy.d/envoy.yaml
      Total Runs: 1
      Metric Samples: Last Run: 546, Total: 546
      Events: Last Run: 0, Total: 0
      Service Checks: Last Run: 1, Total: 1
      Average Execution Time : 25ms
      Last Execution Date : 2020-02-17 00:58:05.000000 UTC
      Last Successful Execution Date : 2020-02-17 00:58:05.000000 UTC
```

### Debugging

You may start an [interactive debugging session](https://docs.python.org/3/library/pdb.html) using the `--breakpoint`/`-b` option.

The option accepts an integer representing the line number at which to break. For convenience, `0` and `-1` are shortcuts to
the first and last line of the integration's `check` method, respectively.

```
$ ddev env check envoy py38 -b 0
> /opt/datadog-agent/embedded/lib/python3.8/site-packages/datadog_checks/envoy/envoy.py(34)check()
-> custom_tags = instance.get('tags', [])
(Pdb) list
 29             self.blacklisted_metrics = set()
 30
 31             self.caching_metrics = None
 32
 33         def check(self, instance):
 34 B->         custom_tags = instance.get('tags', [])
 35
 36             try:
 37                 stats_url = instance['stats_url']
 38             except KeyError:
 39                 msg = 'Envoy configuration setting `stats_url` is required'
(Pdb) print(instance)
{'stats_url': 'http://localhost:8001/stats'}
```

!!! info "Caveat"
    The line number must be within the integration's `check` method.

## Refreshing state

Testing and manual check runs always reflect the current state of code and configuration however, if you want to see the
result of changes [in-app](https://app.datadoghq.com/metric/explorer), you will need to refresh the environment by
running `ddev env reload <INTEGRATION> <ENVIRONMENT>`.

## Removal

To stop an environment run `ddev env stop <INTEGRATION> <ENVIRONMENT>`.

Any environments that haven't been explicitly stopped will show as active in the output of `ddev env ls`, even persisting
through system restarts. If you are confident that environments are no longer active, you can run `ddev env prune` to
remove all accumulated environment state.
