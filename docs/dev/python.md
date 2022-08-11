---
title: The `AgentCheck` base class
kind: documentation
---

The [Base package][datadog-checks-base] provides all the functionality and utilities necessary for writing Agent Integrations. Most importantly it provides the [AgentCheck](api.md#datadog_checks.base.checks.base.AgentCheck) base class from which
every Check must be inherited.

You would use it like so:

```python
from datadog_checks.base import AgentCheck


class AwesomeCheck(AgentCheck):
    __NAMESPACE__ = 'awesome'

    def check(self, instance):
        self.gauge('test', 1.23, tags=['foo:bar'])
```

The `check` method is what the [Datadog Agent][] will execute.

In this example we created a Check and gave it a namespace of `awesome`. This means that by default, every submission's
name will be prefixed with `awesome.`.

We submitted a [gauge][metric-type-gauge] metric named `awesome.test` with a value of `1.23` tagged by `foo:bar`.

The magic hidden by the usability of the API is that this actually calls a [C binding][rtloader] which
communicates with the Agent (written in Go).

The [AgentCheck base class](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/base.py) contains the logic that all Checks inherit.

In addition to the integrations inheriting from AgentCheck, other classes that inherit from AgentCheck include:

- [PDHBaseCheck](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/win/winpdh_base.py)
- [OpenMetricsBaseCheck](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/openmetrics/base_check.py)
- [KubeLeaderElectionBaseCheck](https://github.com/DataDog/integrations-core/blob/master/datadog_checks_base/datadog_checks/base/checks/kube_leader/base_check.py)

## Getting Started

The Datadog Agent looks for `__version__` and a subclass of `AgentCheck` at the root of every Check package.

Below is an example of the `__init__.py` file for a hypothetical `Awesome` Check:

```python
from .__about__ import __version__
from .check import AwesomeCheck

__all__ = ['__version__', 'AwesomeCheck']
```


The version is used in the Agent's status output (if no `__version__` is found, it will default to `0.0.0`):
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

AgentCheck contains functions that you use to execute Checks and submit data to Datadog.

### Metrics

This list enumerates what is collected from your system by each integration. For more information on metrics, see the [Metric Types documentation.](https://docs.datadoghq.com/developers/metrics/types/) You can find the metrics for each integration in that integration's `metadata.csv` file. You can also set up [custom metrics](https://docs.datadoghq.com/developers/metrics/), so if the integration doesn’t offer a metric out of the box, you can usually add it.