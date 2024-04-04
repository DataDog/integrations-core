# Kafka Consumer Integration

![Kafka Dashboard][1]

## Overview

This Agent check only collects metrics for message offsets. If you want to collect JMX metrics from the Kafka brokers or Java-based consumers/producers, see the Kafka check.

If you would benefit from visualizing the topology of your streaming data pipelines, or from investigating localized bottlenecks within your data streams setup, check out [Data Streams Monitoring][16].

This check fetches the highwater offsets from the Kafka brokers, consumer offsets that are stored in Kafka or Zookeeper (for old-style consumers), and the calculated consumer lag (which is the difference between the broker offset and the consumer offset).

**Note:** This integration ensures that consumer offsets are checked before broker offsets; in the worst case, consumer lag may be a little overstated. Checking these offsets in the reverse order can understate consumer lag to the point of having negative values, which is a dire scenario usually indicating messages are being skipped.

## Setup

### Installation

The Agent's Kafka consumer check is included in the [Datadog Agent][2] package. No additional installation is needed on your Kafka nodes.

### Configuration

<!-- xxx tabs xxx -->
<!-- xxx tab "Host" xxx -->

#### Host

To configure this check for an Agent running on a host:

##### Metric collection

1. Edit the `kafka_consumer.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][3]. See the [sample kafka_consumer.d/conf.yaml][4] for all available configuration options.

2. [Restart the Agent][5].

##### Log collection

This check does not collect additional logs. To collect logs from Kafka brokers, see [log collection instructions for Kafka][6].

<!-- xxz tab xxx -->
<!-- xxx tab "Containerized" xxx -->

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][17] for guidance on applying the parameters below.

##### Metric collection

| Parameter            | Value                                |
| -------------------- | ------------------------------------ |
| `<INTEGRATION_NAME>` | `kafka_consumer`                     |
| `<INIT_CONFIG>`      | blank or `{}`                        |
| `<INSTANCE_CONFIG>`  | `{"kafka_connect_str": <KAFKA_CONNECT_STR>}` <br/>For example, `{"kafka_connect_str": "server:9092"}` |

##### Log collection

This check does not collect additional logs. To collect logs from Kafka brokers, see [log collection instructions for Kafka][6].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

### Validation

[Run the Agent's status subcommand][8] and look for `kafka_consumer` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][9] for a list of metrics provided by this check.

### Events

**consumer_lag**:<br>
The Datadog Agent emits an event when the value of the `consumer_lag` metric goes below 0, tagging it with `topic`, `partition` and `consumer_group`.

### Service Checks

The Kafka-consumer check does not include any service checks.

## Troubleshooting

- [Troubleshooting and Deep Dive for Kafka][10]
- [Agent failed to retrieve RMIServer stub][11]

**Kerberos GSSAPI Authentication**

Depending on your Kafka cluster's Kerberos setup, you may need to configure the following:

* Kafka client configured for the Datadog Agent to connect to the Kafka broker. The Kafka client should be added as a Kerberos principal and added to a Kerberos keytab. The Kafka client should also have a valid kerberos ticket. 
* TLS certificate to authenticate a secure connection to the Kafka broker.
  * If JKS keystore is used, a certificate needs to be exported from the keystore and the file path should be configured with the applicable `tls_cert` and/or `tls_ca_cert` options. 
  * If a private key is required to authenticate the certificate, it should be configured with the `tls_private_key` option. If applicable, the private key password should be configured with the `tls_private_key_password`. 
* `KRB5_CLIENT_KTNAME` environment variable pointing to the Kafka client's Kerberos keytab location if it differs from the default path (for example, `KRB5_CLIENT_KTNAME=/etc/krb5.keytab`)
* `KRB5CCNAME` environment variable pointing to the Kafka client's Kerberos credentials ticket cache if it differs from the default path (for example, `KRB5CCNAME=/tmp/krb5cc_xxx`)
* If the Datadog Agent is unable to access the environment variables, configure the environment variables in a Datadog Agent service configuration override file for your operating system. The procedure for modifying the Datadog Agent service unit file may vary for different Linux operating systems. For example, in a Linux `systemd` environment: 

**Linux Systemd Example**

1. Configure the environment variables in an environment file.
   For example: `/path/to/environment/file`

  ```
  KRB5_CLIENT_KTNAME=/etc/krb5.keytab
  KRB5CCNAME=/tmp/krb5cc_xxx
  ```

2. Create a Datadog Agent service configuration override file: `sudo systemctl edit datadog-agent.service`

3. Configure the following in the override file:

  ```
  [Service]
  EnvironmentFile=/path/to/environment/file
  ```

4. Run the following commands to reload the systemd daemon, datadog-agent service, and Datadog Agent:

```
sudo systemctl daemon-reload
sudo systemctl restart datadog-agent.service
sudo service datadog-agent restart
```

## Further Reading

- [Monitoring Kafka performance metrics][13]
- [Collecting Kafka performance metrics][14]
- [Monitoring Kafka with Datadog][15]

[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/kafka_consumer/images/kafka_dashboard.png
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[4]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/datadog_checks/kafka_consumer/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/integrations/kafka/#log-collection
[7]: https://docs.datadoghq.com/agent/guide/autodiscovery-with-jmx/?tab=containerizedagent
[8]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[9]: https://github.com/DataDog/integrations-core/blob/master/kafka_consumer/metadata.csv
[10]: https://docs.datadoghq.com/integrations/faq/troubleshooting-and-deep-dive-for-kafka/
[11]: https://docs.datadoghq.com/integrations/guide/agent-failed-to-retrieve-rmiserver-stub/
[13]: https://www.datadoghq.com/blog/monitoring-kafka-performance-metrics
[14]: https://www.datadoghq.com/blog/collecting-kafka-performance-metrics
[15]: https://www.datadoghq.com/blog/monitor-kafka-with-datadog
[16]: https://www.datadoghq.com/product/data-streams-monitoring/
[17]: https://docs.datadoghq.com/containers/kubernetes/integrations/
