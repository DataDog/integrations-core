# JMX integrations

JMX integrations (ActiveMQ, Kafka, Confluent Platform, etc) use [JMXFetch](https://github.com/DataDog/jmxfetch) to collect metrics.

A minimal config looks like this:

```yaml
init_config:
    is_jmx: true
    collect_default_metrics: true

instances:
  - host: <HOST>
    port: <PORT>
```

- `init_config.is_jmx` tells the Agent that the integration is a JMX type of integration
- `init_config.collect_default_metrics` will enable collecting metrics declared in `metrics.yaml`

