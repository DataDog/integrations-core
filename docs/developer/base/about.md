# About

-----

The package `datadog-checks-base` provides all the functionality and utilities necessary for writing Agent Integrations.
Most importantly it provides the [AgentCheck](api.md#agentcheck) base class from which every Check must be inherited.

You would use it like so:

```python
from datadog_checks.base import AgentCheck


class AwesomeCheck(AgentCheck):
    __NAMESPACE__ = 'awesome'

    def check(self, instance):
        self.gauge('test', 1.23, tags=['foo:bar'])
```

The `check` method is what the [Datadog Agent](https://docs.datadoghq.com/agent/) will execute.

In this example we created a Check and gave it a namespace of `awesome`. This means that by default, every submission's
name will be prefixed with `awesome.`.

We submitted a [gauge](https://docs.datadoghq.com/developers/metrics/types/?tab=gauge#metric-type-definition) metric named
`awesome.test` with a value of `1.23` tagged by `foo:bar`.

The magic hidden by the usability of the API is that this actually calls a [C binding](https://github.com/DataDog/datadog-agent/tree/master/rtloader) which
communicates with the Agent (written in Go).

<br>

<div align="center">
    <video preload="auto" autoplay loop muted>
        <source src="https://media.giphy.com/media/Um3ljJl8jrnHy/giphy.mp4" type="video/mp4"></source>
    </video>
</div>
