# JMX integration

Tutorial for starting a JMX integration

## Step 1: Create a JMX integration scaffolding

```bash
ddev create --type jmx MyJMXIntegration
```

JMX integration contains specific init configs and instance configs:

```yaml
init_config:
    is_jmx: true                   # tells the Agent that the integration is a JMX type of integration
    collect_default_metrics: true  # if true, metrics declared in `metrics.yaml` are collected

instances:
  - host: <HOST>                   # JMX hostname
    port: <PORT>                   # JMX port
    ...
```

Other init and instance configs can be found on [JMX integration page](https://docs.datadoghq.com/integrations/java)

## Step 2: Define metrics you want to collect

Select what metrics you want to collect from JMX. Available metrics can be usually found on official documentation of the service you want to monitor.

You can also use tools like [VisualVM](https://visualvm.github.io/), [JConsole](https://docs.oracle.com/javase/7/docs/technotes/guides/management/jconsole.html) or [jmxterm](https://datadoghq.dev/integrations-core/tutorials/jmx/tools/) to explore the available JMX beans and their descriptions.


## Step 3: Define metrics filters

Edit the `metrics.yaml` to define the filters for collecting metrics.

The metrics filters format details can be found on [JMX integration doc](https://docs.datadoghq.com/integrations/java/?tab=host#description-of-the-filters)

[JMXFetch test cases](https://github.com/DataDog/jmxfetch/tree/master/src/test/resources) also help understanding how metrics filters work and provide many examples.  

Example of `metrics.yaml`

```yaml
jmx_metrics:
  - include:
      domain: org.apache.activemq
      destinationType: Queue
      attribute:
        AverageEnqueueTime:
          alias: activemq.queue.avg_enqueue_time
          metric_type: gauge
        ConsumerCount:
          alias: activemq.queue.consumer_count
          metric_type: gauge
```

### Testing

Using [`ddev` tool](https://datadoghq.dev/integrations-core/ddev/cli/), you can test against the JMX service by providing a `dd_environment` in `tests/conftest.py` like this one:

```python
@pytest.fixture(scope="session")
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    with docker_run(
        compose_file,
        conditions=[
            # Kafka Broker
            CheckDockerLogs('broker', 'Monitored service is now ready'),
        ],
    ):
        yield CHECK_CONFIG, {'use_jmx': True}
```

And a `e2e` test like:

```python

@pytest.mark.e2e
def test(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance)

    for metric in ACTIVEMQ_E2E_METRICS + JVM_E2E_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS)
```

Real examples of:

- [JMX dd_environment](https://github.com/DataDog/integrations-core/blob/master/activemq/tests/conftest.py)
- [JMX e2e test](https://github.com/DataDog/integrations-core/blob/master/activemq/tests/test_check.py)
