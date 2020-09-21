# Building JMX integration

## Step 1: Create a JMX integration scaffolding using:

```bash
ddev create --type jmx MyJMXIntegration
```

JMX integration contains specific init configs and instance configs:

```yaml
init_config:
    is_jmx: true                   # tells the Agent that the integration is a JMX type of integration
    collect_default_metrics: true  # if true, metrics declared in `metrics.yaml` are collected

instances:
  - host: <HOST>
    port: <PORT>
    ...
```

Other instance configs can be found in on [JMX integration page](https://docs.datadoghq.com/integrations/java)

## Step 2: Define metrics you want to collect

Select what metrics you want to collect from JMX. You can use:

- official documentation of the service you want to monitor
- VisualVM, JConsole or jmxterm to explore the available beans and their descriptions


## Step 3: Define metrics filters

Edit the `metrics.yaml` to define the filters for collecting the metrics.

The metrics filters format details can be found on [JMX integration page](https://docs.datadoghq.com/integrations/java)

[JMXFetch test cases](https://github.com/DataDog/jmxfetch/tree/master/src/test/resources) also help understand how metrics filters work.  

### Testing

You can test against the JMX service by providing a `dd_environment` like this one:

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

Real example with ActiveMQ:
- [dd_environment](https://github.com/DataDog/integrations-core/blob/master/activemq/tests/conftest.py).
- [e2e test](https://github.com/DataDog/integrations-core/blob/master/activemq/tests/test_check.py).
