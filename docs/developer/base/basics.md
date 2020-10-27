# Basics

-----

The AgentCheck base class in base.py contains the logic that all Checks inherit.

In addition to the integrations inheriting from AgentCheck, other classes that inherit from AgentCheck include:

- [PDHBaseCheck](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/win/winpdh_base.py)
- [OpenMetricsBaseCheck](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/openmetrics/base_check.py)
- [GenericPrometheusCheck](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/prometheus/base_check.py)
- [PrometheusCheck](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/prometheus/prometheus_base.py)
- [KubeLeaderElectionBaseCheck](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/kube_leader/base_check.py)


## Getting Started
In each Check, Datadog looks for `__version__` and a subclass of AgentCheck at the root of every package.

Below is an example of the `__init__.py` folder for AwesomeCheck:
```python
# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .check import AwesomeCheck

__all__ = ['__version__', 'AwesomeCheck']
```

Note that we look for `__version__` in `__about__.py` in this case, however it does not necessarily need to be put there. 

This value is used in Datadog's check:

```
=========
Collector
=========

  Running Checks
  ==============

    AwesomeCheck (0.0.1)
    -------------------
      Instance ID: 1234 [OK]
      Configuration Source: file:/etc/datadog-agent/conf.d/awesomecheck.d/awesomecheck.yaml
      Total Runs: 12
      Metric Samples: Last Run: 242, Total: 2,904
      Events: Last Run: 0, Total: 0
      Service Checks: Last Run: 0, Total: 0
      Average Execution Time : 49ms
      Last Execution Date : 2020-10-26 19:09:22.000000 UTC
      Last Successful Execution Date : 2020-10-26 19:09:22.000000 UTC

...
```

## Checks
AgentCheck contains functions that you use to execute checks and submit data to Datadog.

include link to the app for each 

### Metrics
The list of what is collected from your system by each integration. More information on metrics can be found [here.](https://docs.datadoghq.com/developers/metrics/types/) You can find the metrics for each integration in that integrations metadata.csv file. You can also set up [custom metrics](https://docs.datadoghq.com/developers/metrics/), so if the integration doesn’t offer a metric out of the box, you can usually add it.

#### Gauge
The gauge metric submission type represents a snapshot of events in one time interval. This representative snapshot value is the last value submitted to the Agent during a time interval. A gauge can be used to take a measure of something reporting continuously—like the available disk space or memory used.

More information on this can be found in the API docs [here.](https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.gauge)

#### Count
The count metric submission type represents the total number of event occurrences in one time interval. A count can be used to track the total number of connections made to a database or the total number of requests to an endpoint. This number of events can accumulate or decrease over time—it is not monotonically increasing.

More information on this can be found in the API docs [here.](https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.count)

#### Monotonic Count
Similar to Count, Monotonic Count represents the total number of event occurrences in one time interval, however this value can ONLY increment.

More information on this can be found in the API docs [here.](https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.monotonic_count)

#### Rate
The rate metric submission type represents the total number of event occurrences per second in one time interval. A rate can be used to track how often something is happening—like the frequency of connections made to a database or the flow of requests made to an endpoint.

More information on this can be found in the API docs [here.](https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.rate)

#### Histogram
The histogram metric submission type represents the statistical distribution of a set of values calculated Agent-side in one time interval. Datadog’s histogram metric type is an extension of the StatsD timing metric type: the Agent aggregates the values that are sent in a defined time interval and produces different metrics which represent the set of values.

More information on this can be found in the API docs [here.](https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.histogram)

#### Historate
Similar to the histogram metric, the historate represents statistical distribution over one time interval, although this is based on rate metrics.

More information on this can be found in the API docs [here.](https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.historate)

### Service Checks
Service checks are a type of monitor used to track the uptime status of the service. For more information, see the [Service checks](https://docs.datadoghq.com/developers/service_checks/) guide.

More information on this can be found in the API docs [here.](https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.service_check)

### Events
Events are informational messages about your system that are consumed by [the events stream](https://app.datadoghq.com/event/stream) so that you can build monitors on them.

More information on this can be found in the API docs [here.](https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.event)

## Namespacing
Within every integration, you can specify the value of `__NAMESPACE__`:
```python
from datadog_checks.base import AgentCheck


class AwesomeCheck(AgentCheck):
    __NAMESPACE__ = 'awesome'

...
```
This is an optional addition, but it makes submissions easier since it prefixes every metric with the `__NAMESPACE__` automatically. In this case it would append `awesome.` to each metric submitted to Datadog.

If you wish to ignore the namespace for any reason, you can append optional bool `raw=True` to each submission:
```python
...

self.gauge('test', 1.23, tags=['foo:bar'], raw=True)

...
```
We submitted a gauge metric named `awesome.test` with a value of `1.23` tagged by `foo:bar` ignoring the namespace.

## Check Initializations
In the AgentCheck class, there is a useful property called `check_initializations`, which we use to execute functions that are called once before the first check run.
We can fill up `check_initializations` with instructions in `__init__` function of integrations. For example, we could use it to parse configuration information before running a check. Listed below is an example with Airflow:

```python
class AirflowCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(AirflowCheck, self).__init__(name, init_config, instances)

        self._url = self.instance.get('url', '')
        self._tags = self.instance.get('tags', [])

        # The Agent only makes one attempt to instantiate each AgentCheck so any errors occurring
        # in `__init__` are logged just once, making it difficult to spot. Therefore, we emit
        # potential configuration errors as part of the check run phase.
        # The configuration is only parsed once if it succeed, otherwise it's retried.
        self.check_initializations.append(self._parse_config)

...
```

Before the first Airflow check is ran, `self._parse_config` will be executed in `base.py`'s `run()` function:
```python
# base.py

    def run(self):
        # type: () -> str
        try:
            while self.check_initializations:
                initialization = self.check_initializations.popleft()
                try:
                    initialization()
                except Exception:
                    self.check_initializations.appendleft(initialization)
                    raise
    ...

```