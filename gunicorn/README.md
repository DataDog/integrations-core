# Gunicorn Integration

## Overview

The Datadog Agent collects one main metric about Gunicorn: the number of worker processes running. It also sends one service check: whether or not Gunicorn is running.

Gunicorn itself can provide further metrics via DogStatsD, including those for:

* Total request rate
* Request rate by status code (2xx, 3xx, 4xx, 5xx)
* Request duration (average, median, max, 95th percentile, etc)
* Log message rate by log level (critical, error, warning, exception)

## Setup
### Installation

The Datadog Agent's Gunicorn check is included in the Agent package, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Gunicorn servers.

If you need the newest version of the Gunicorn check, install the `dd-check-gunicorn` package; this package's check will override the one packaged with the Agent. See the [integrations-core repository README.md for more details](https://docs.datadoghq.com/agent/faq/install-core-extra/).

The Gunicorn check requires your Gunicorn app's Python environment to have the [`setproctitle`](https://pypi.python.org/pypi/setproctitle) package; without it, the Datadog Agent will always report that it cannot find a `gunicorn` master process (and hence, cannot find workers, either). Install the `setproctitle` package in your app's Python environment if you want to collect the `gunicorn.workers` metric.

### Configuration
#### Configure the Datadog Agent

Create a `gunicorn.yaml` in the Datadog Agent's `conf.d` directory. See the [sample gunicorn.yaml](https://github.com/DataDog/integrations-core/blob/master/gunicorn/conf.yaml.example) for all available configuration options:

```
init_config:

instances:
  # as set
  # 1) in your app's config.py (proc_name = <YOUR_APP_NAME>), OR
  # 2) via CLI (gunicorn --name <YOUR_APP_NAME> your:app)
  - proc_name: <YOUR_APP_NAME>
```

[Restart the Agent](https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent) to begin sending Gunicorn metrics to Datadog.

#### Connect Gunicorn to DogStatsD

Since version 19.1, Gunicorn [provides an option](http://docs.gunicorn.org/en/stable/settings.html#statsd-host) to send its metrics to a daemon that implements the StatsD protocol, such as [DogStatsD](https://docs.datadoghq.com/guides/dogstatsd). As with many Gunicorn options, you can either pass it to `gunicorn` on the CLI (`--statsd-host`) or set it in your app's configuration file (`statsd_host`). Configure your app to send metrics to DogStatsD at `"localhost:8125"`, and restart the app.

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `gunicorn` under the Checks section:

```
  Checks
  ======
    [...]

    gunicorn (5.12.1)
    -----------------
      - instance #0 [OK]
      - Collected 2 metrics, 0 events & 1 service check

    [...]
```

If the status is not OK, see the Troubleshooting section.

Use `netstat` to verify that Gunicorn is sending _its_ metrics, too:

```
$ sudo netstat -nup | grep "127.0.0.1:8125.*ESTABLISHED"
udp        0      0 127.0.0.1:38374         127.0.0.1:8125          ESTABLISHED 15500/gunicorn: mas
```

## Compatibility

The gunicorn check is compatible with all major platforms.

## Data Collected
### Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/gunicorn/metadata.csv) for a list of metrics provided by this integration.

### Events
The Gunicorn check does not include any event at this time.

### Service Checks

`gunicorn.is_running`:

Returns CRITICAL if the Agent cannot find a Gunicorn master process, or if cannot find any working or idle worker processes.


## Troubleshooting
### Agent cannot find Gunicorn process
```
  Checks
  ======

    gunicorn (5.12.1)
    -----------------
      - instance #0 [ERROR]: 'Found no master process with name: gunicorn: master [my_web_app]'
      - Collected 0 metrics, 0 events & 1 service check
      - Dependencies:
          - psutil: 4.4.1
```

Either Gunicorn really isn't running, or your app's Python environment doesn't have the `setproctitle` package installed.

If `setproctitle` is not installed, Gunicorn appears in the process table like so:

```
$ ps -ef | grep gunicorn
ubuntu   18013 16695  2 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
ubuntu   18018 18013  0 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
ubuntu   18019 18013  0 20:23 pts/0    00:00:00 /usr/bin/python /usr/bin/gunicorn --config test-app-config.py gunicorn-test:app
```

If it _is_ installed, `gunicorn` processes appear in the format the Datadog Agent expects:

```
$ ps -ef | grep gunicorn
ubuntu   18457 16695  5 20:26 pts/0    00:00:00 gunicorn: master [my_app]
ubuntu   18462 18457  0 20:26 pts/0    00:00:00 gunicorn: worker [my_app]
ubuntu   18463 18457  0 20:26 pts/0    00:00:00 gunicorn: worker [my_app]
```

## Further Reading
To get a better idea of how (or why) to integrate your Gunicorn apps with Datadog, check out our [blog post](https://www.datadoghq.com/blog/monitor-gunicorn-performance/).
