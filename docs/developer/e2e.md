# E2E

-----

Any integration that makes use of our [pytest plugin](ddev/plugins.md#pytest) in its test suite supports
end-to-end testing on a live [Datadog Agent][].

The entrypoint for E2E management is the command group [`env`](ddev/cli.md#ddev-env).

## Discovery

Use the `show` command to see what environments are available, for example:

```
$ ddev env show postgres
  Available
┏━━━━━━━━━━━━┓
┃ Name       ┃
┡━━━━━━━━━━━━┩
│ py3.9-9.6  │
├────────────┤
│ py3.9-10.0 │
├────────────┤
│ py3.9-11.0 │
├────────────┤
│ py3.9-12.1 │
├────────────┤
│ py3.9-13.0 │
├────────────┤
│ py3.9-14.0 │
└────────────┘
```

You'll notice that only environments that actually run tests are available.

Running simply `ddev env show` with no arguments will display the active environments.

## Creation

To start an environment run `ddev env start <INTEGRATION> <ENVIRONMENT>`, for example:

```
$ ddev env start postgres py3.9-14.0
────────────────────────────────────── Starting: py3.9-14.0 ──────────────────────────────────────
[+] Running 4/4
 - Network compose_pg-net                 Created                                            0.1s
 - Container compose-postgres_replica2-1  Started                                            0.9s
 - Container compose-postgres_replica-1   Started                                            0.9s
 - Container compose-postgres-1           Started                                            0.9s

master-py3: Pulling from datadog/agent-dev
Digest: sha256:72824c9a986b0ef017eabba4e2cc9872333c7e16eec453b02b2276a40518655c
Status: Image is up to date for datadog/agent-dev:master-py3
docker.io/datadog/agent-dev:master-py3

Stop environment -> ddev env stop postgres py3.9-14.0
Execute tests -> ddev env test postgres py3.9-14.0
Check status -> ddev env agent postgres py3.9-14.0 status
Trigger run -> ddev env agent postgres py3.9-14.0 check
Reload config -> ddev env reload postgres py3.9-14.0
Manage config -> ddev env config
Config file -> C:\Users\ofek\AppData\Local\ddev\env\postgres\py3.9-14.0\config\postgres.yaml
```

This sets up the selected environment and an instance of the Agent running in a Docker container. The default
configuration is defined by each environment's test suite and is saved to a file, which is then mounted to the
Agent container so you may freely modify it.

Let's see what we have running:

```
$ docker ps --format "table {{.Image}}\t{{.Status}}\t{{.Ports}}\t{{.Names}}"
IMAGE                          STATUS                   PORTS                              NAMES
datadog/agent-dev:master-py3   Up 3 minutes (healthy)                                      dd_postgres_py3.9-14.0
postgres:14-alpine             Up 3 minutes (healthy)   5432/tcp, 0.0.0.0:5434->5434/tcp   compose-postgres_replica2-1
postgres:14-alpine             Up 3 minutes (healthy)   0.0.0.0:5432->5432/tcp             compose-postgres-1
postgres:14-alpine             Up 3 minutes (healthy)   5432/tcp, 0.0.0.0:5433->5433/tcp   compose-postgres_replica-1
```

### Agent version

You can select a particular build of the Agent to use with the `--agent`/`-a` option. Any Docker image is valid e.g. `datadog/agent:7.47.0`.

A custom nightly build will be used by default, which is re-built on every commit to the [Datadog Agent repository][datadog-agent].

### Integration version

By default the version of the integration used will be the one shipped with the chosen Agent version. If you wish
to modify an integration and test changes in real time, use the `--dev` flag.

Doing so will mount and install the integration in the Agent container. All modifications to the integration's directory will be propagated to the Agent,
whether it be a code change or switching to a different Git branch.

If you modify the [base package](base/about.md) then you will need to mount that with the `--base` flag, which implicitly activates `--dev`.

## Testing

To run tests against the live Agent, use the `ddev env test` command. It is similar to the [test command](testing.md#usage) except
it is capable of running tests [marked as E2E](ddev/plugins.md#agent-check-runner), and only runs such tests.

## Agent invocation

You can invoke the Agent with arbitrary arguments using `ddev env agent <INTEGRATION> <ENVIRONMENT> [ARGS]`, for example:

```
$ ddev env agent postgres py3.9-14.0 status
Getting the status from the agent.


==================================
Agent (v7.49.0-rc.2+git.5.2fe7360)
==================================

  Status date: 2023-10-06 05:16:45.079 UTC (1696569405079)
  Agent start: 2023-10-06 04:58:26.113 UTC (1696568306113)
  Pid: 395
  Go Version: go1.20.8
  Python Version: 3.9.17
  Build arch: amd64
  Agent flavor: agent
  Check Runners: 4
  Log Level: info

...
```

Invoking the Agent's `check` command is special in that you may omit its required integration argument:

```
$ ddev env agent postgres py3.9-14.0 check --log-level debug
...
=========
Collector
=========

  Running Checks
  ==============

    postgres (15.0.0)
    -----------------
      Instance ID: postgres:973e44c6a9b27d18 [OK]
      Configuration Source: file:/etc/datadog-agent/conf.d/postgres.d/postgres.yaml
      Total Runs: 1
      Metric Samples: Last Run: 2,971, Total: 2,971
      Events: Last Run: 0, Total: 0
      Database Monitoring Metadata Samples: Last Run: 3, Total: 3
      Service Checks: Last Run: 1, Total: 1
      Average Execution Time : 259ms
      Last Execution Date : 2023-10-06 05:07:28 UTC (1696568848000)
      Last Successful Execution Date : 2023-10-06 05:07:28 UTC (1696568848000)


  Metadata
  ========
    config.hash: postgres:973e44c6a9b27d18
    config.provider: file
    resolved_hostname: ozone
    version.major: 14
    version.minor: 9
    version.patch: 0
    version.raw: 14.9
    version.scheme: semver
```

## Debugging

You may start an [interactive debugging session][python-pdb] using the `--breakpoint`/`-b` option.

The option accepts an integer representing the line number at which to break. For convenience, `0` and `-1` are shortcuts to
the first and last line of the integration's `check` method, respectively.

```
$ ddev env agent postgres py3.9-14.0 check -b 0
> /opt/datadog-agent/embedded/lib/python3.9/site-packages/datadog_checks/postgres/postgres.py(851)check()
-> tags = copy.copy(self.tags)
(Pdb) list
846                 }
847                 self._database_instance_emitted[self.resolved_hostname] = event
848                 self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))
849
850         def check(self, _):
851 B->         tags = copy.copy(self.tags)
852             # Collect metrics
853             try:
854                 # Check version
855                 self._connect()
856                 self.load_version()  # We don't want to cache versions between runs to capture minor updates for metadata
```

!!! info "Caveat"
    The line number must be within the integration's `check` method.

## Refreshing state

Testing and manual check runs always reflect the current state of code and configuration however, if you want to see the result
of changes [in-app][], you will need to refresh the environment by running `ddev env reload <INTEGRATION> <ENVIRONMENT>`.

## Removal

To stop an environment run `ddev env stop <INTEGRATION> <ENVIRONMENT>`.

Any environments that haven't been explicitly stopped will show as active in the output of `ddev env show`, even persisting
through system restarts.
