# Spark Check

![Spark Graph][1]

## Overview

This check monitors [Spark][13] through the Datadog Agent. Collect Spark metrics for:

* Drivers and executors: RDD blocks, memory used, disk used, duration, etc.
* RDDs: partition count, memory used, and disk used
* Tasks: number of tasks active, skipped, failed, and total
* Job state: number of jobs active, completed, skipped, and failed

## Setup
### Installation

The Spark check is included in the [Datadog Agent][3] package. No additional installation is needed on your:

* Mesos master (for Spark on Mesos),
* YARN ResourceManager (for Spark on YARN), or
* Spark master (for Standalone Spark)

### Configuration
#### Host

Follow the instructions below to configure this check for an Agent running on a host. For containerized environments, see the [Containerized](#containerized) section.

1. Edit the `spark.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4]. The following parameters may require updating. See the [sample spark.d/conf.yaml][5] for all available configuration options.

    ```yaml
        init_config:

        instances:
          - spark_url: http://localhost:8088 # Spark master web UI
        #   spark_url: http://<Mesos_master>:5050 # Mesos master web UI
        #   spark_url: http://<YARN_ResourceManager_address>:8088 # YARN ResourceManager address

            spark_cluster_mode: spark_standalone_mode # default
        #   spark_cluster_mode: spark_mesos_mode
        #   spark_cluster_mode: spark_yarn_mode
        #   spark_cluster_mode: spark_driver_mode

            cluster_name: <CLUSTER_NAME> # required; adds a tag 'cluster_name:<CLUSTER_NAME>' to all metrics
        #   spark_pre_20_mode: true   # if you use Standalone Spark < v2.0
        #   spark_proxy_enabled: true # if you have enabled the spark UI proxy
    ```

2. [Restart the Agent][6].

#### Containerized

For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying the parameters below.

| Parameter            | Value                                                             |
|----------------------|-------------------------------------------------------------------|
| `<INTEGRATION_NAME>` | `spark`                                                           |
| `<INIT_CONFIG>`      | blank or `{}`                                                     |
| `<INSTANCE_CONFIG>`  | `{"spark_url": "%%host%%:8080", "cluster_name":"<CLUSTER_NAME>"}` |

### Validation

Run the Agent's [status subcommand][7] and look for `spark` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][8] for a list of metrics provided by this check.

### Events
The Spark check does not include any events.

### Service Checks
The Agent submits one of the following service checks, depending on how you're running Spark:

**spark.standalone_master.can_connect**<br>
Returns `CRITICAL` if the Agent is unable to connect to the Spark instance's Standalone Master. Returns `OK` otherwise.

**spark.mesos_master.can_connect**<br>
Returns `CRITICAL` if the Agent is unable to connect to the Spark instance's Mesos Master. Returns `OK` otherwise.

**spark.application_master.can_connect**<br>
Returns `CRITICAL` if the Agent is unable to connect to the Spark instance's ApplicationMaster. Returns `OK` otherwise.

**spark.resource_manager.can_connect**<br>
Returns `CRITICAL` if the Agent is unable to connect to the Spark instance's ResourceManager. Returns `OK` otherwise.

**spark.driver.can_connect**<br>
Returns `CRITICAL` if the Agent is unable to connect to the Spark instance's ResourceManager. Returns `OK` otherwise.

## Troubleshooting
### Spark on AWS EMR

To receive metrics for Spark on AWS EMR, [use bootstrap actions][9] to install the [Datadog Agent][10] and then create the `/etc/dd-agent/conf.d/spark.yaml` configuration file with the [proper values on each EMR node][11].

## Further Reading

Additional helpful documentation, links, and articles:

* [Hadoop & Spark monitoring with Datadog][12]


[1]: https://raw.githubusercontent.com/DataDog/integrations-core/master/spark/images/sparkgraph.png
[2]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[3]: https://app.datadoghq.com/account/settings#agent
[4]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/#agent-configuration-directory
[5]: https://github.com/DataDog/integrations-core/blob/master/spark/datadog_checks/spark/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/spark/metadata.csv
[9]: https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-bootstrap.html
[10]: https://docs.datadoghq.com/agent
[11]: https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-connect-master-node-ssh.html
[12]: https://www.datadoghq.com/blog/monitoring-spark
[13]: https://spark.apache.org/
