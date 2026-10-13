# Agent Check: Kyverno

## Overview

This check monitors [Kyverno][1] through the Datadog Agent.

**Minimum Agent version:** 7.55.0

## Setup

Follow the instructions below to install and configure this check for an Agent running in your Kubernetes environment. For more information about configuration in containerized environments, see the [Autodiscovery Integration Templates][3] for guidance.

### Installation

Starting from Agent release 7.56.0, the Kyverno check is included in the [Datadog Agent][2] package. No additional installation is needed in your environment.

This check uses [OpenMetrics][5] to collect metrics from the OpenMetrics endpoint that Kyverno exposes, which requires Python 3.

### Configuration

Kyverno consists of multiple controllers such as Backup, Admissions, Cleanup, and Reports controllers. Each of these controllers can be monitored. Each Kyverno controller has Prometheus-formatted metrics readily available at `/metrics` on port `8000`. Configure each controller with one of the Kubernetes Autodiscovery options below. You can find additional configuration options by reviewing the [sample kyverno.d/conf.yaml][4].

**Note**: The listed metrics can only be collected if they are available. Some metrics are generated only when certain actions are performed. For example, the `kyverno.controller.drop.count` metric is exposed only after an object is dropped by a controller.

**Note**: Kyverno policy types based on Common Expression Language (CEL) each report their own metrics, namespaced under `kyverno.validating.policy.*`, `kyverno.mutating.policy.*`, `kyverno.image.validating.policy.*`, and `kyverno.generating.policy.*`. These metrics are policy-level rather than rule-level. Unlike the older `kyverno.policy.*` metrics, they carry no `rule_name`, `rule_type`, or `policy_type` tags. They report the execution cause and outcome through the `execution_cause` and `result` tags instead of `rule_execution_cause` and `rule_result`. Account for these differences when you migrate dashboards and monitors away from the older metrics.

**Note**: If you collected any of the CEL-based policy metrics through `extra_metrics` before the Kyverno check supported them, the result depends on how you wrote each entry:
- An entry that names a metric exactly, such as `kyverno_validating_policy_results`, still takes precedence and keeps submitting under the name you chose. To use the names listed in the previous note, remove the entry.
- An entry that matches by pattern, such as `^kyverno_.*_policy_.*`, no longer applies to these metrics, because an exact mapping is matched before a pattern. These metrics are reported under the names listed in the previous note instead of the raw upstream names. Update any dashboards and monitors that reference the old names.

The only parameter required for configuring the Kyverno check is:
- `openmetrics_endpoint`: This parameter should be set to the location where the Prometheus-formatted metrics are exposed. The default port is `8000`. In containerized environments, `%%host%%` should be used for [host autodetection][3]. 

<!-- xxx tabs xxx -->
<!-- xxx tab "Kubernetes annotations" xxx -->

```yaml
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: '<POD_NAME>'
  annotations:
    ad.datadoghq.com/<CONTAINER_NAME>.checks: |
      {
        "kyverno": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8000/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: <CONTAINER_NAME> # e.g. 'kyverno' in the Admission controller
# (...)
```

To collect metrics from each Kyverno controller, the above pod annotations can be applied to each Kyverno controller pod. Example pod annotations for the Reports controller:

```yaml
# Pod manifest from a basic Helm chart deployment
apiVersion: v1
kind: Pod
# (...)
metadata:
  name: 'controller'
  annotations:
    ad.datadoghq.com/<CONTAINER_NAME>.checks: |
      {
        "kyverno": {
          "init_config": {},
          "instances": [
            {
              "openmetrics_endpoint": "http://%%host%%:8000/metrics"
            }
          ]
        }
      }
    # (...)
spec:
  containers:
    - name: controller
# (...)
```
<!-- xxz tab xxx -->
<!-- xxx tab "DatadogInstrumentation CRD" xxx -->

This example targets the Reports Controller Deployment. Create a separate resource for each additional Kyverno controller that you monitor:

```yaml
apiVersion: datadoghq.com/v1alpha1
kind: DatadogInstrumentation
metadata:
  name: <CR_NAME>
  namespace: <WORKLOAD_NAMESPACE>
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kyverno-reports-controller
  config:
    checks:
      - integration: kyverno
        containerName: controller
        initConfig: {}
        instances:
          - openmetrics_endpoint: "http://%%host%%:8000/metrics"
```

For setup details, see [Configure Autodiscovery with the DatadogInstrumentation CRD][11].

<!-- xxz tab xxx -->
<!-- xxz tabs xxx -->

#### Log collection

_Available for Agent versions >6.0_

Kyverno logs can be collected from the different Kyverno pods through Kubernetes. Collecting logs is disabled by default in the Datadog Agent. To enable it, see [Kubernetes Log Collection][10].

See the [Autodiscovery Integration Templates][3] for guidance on applying the parameters below.

| Parameter      | Value                                                   |
| -------------- | ------------------------------------------------------- |
| `<LOG_CONFIG>` | `{"source": "kyverno", "service": "<SERVICE_NAME>"}`  |

### Validation

[Run the Agent's status subcommand][6] and look for `kyverno` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

### Events

The kyverno integration does not include any events.

### Service Checks

The kyverno integration does not include any service checks.

See [service_checks.json][8] for a list of service checks provided by this integration.

## Troubleshooting

Need help? Contact [Datadog support][9].


[1]: https://kyverno.io/docs/introduction/
[2]: /account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/kyverno/datadog_checks/kyverno/data/conf.yaml.example
[5]: https://docs.datadoghq.com/integrations/openmetrics/
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/kyverno/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/kyverno/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
[10]: https://docs.datadoghq.com/agent/kubernetes/log/
[11]: https://docs.datadoghq.com/containers/guide/configure-autodiscovery-with-the-datadoginstrumentation-crd/
