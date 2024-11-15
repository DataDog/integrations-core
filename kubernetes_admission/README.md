# Agent Check: Kubernetes Admission

## Overview

Kubernetes Admission will generate Datadog Events for Kubernetes Admission Requests.

The Kubernetes Admission for Datadog's Cluster Agent offers an easy-to-deploy solution for tracking and monitoring Kubernetes Admission activity.
By sending real-time Datadog Events for every request, it provides comprehensive visibility and enhances security.

## Setup

### Installation

The Kubernetes Admission check is included in the [Datadog Agent][1] package.
No additional installation is needed on your server.

### Configuration

You can activate this feature by activating the `admission_controller_kubernetes_admission_events` setting.

### Validation

You can check the existence of the `kubernetes_admission_events` Validation Webhook using the following command:

```shell
kubectl describe validatingwebhookconfigurations.admissionregistration.k8s.io datadog-webhook
```

You should be able to see the `datadog.webhook.kubernetes.admission.events` webhook in the output.

You can also check that the Datadog Events are being sent by looking at the `kubernetes_admission` events in the Datadog Event Stream.

## Data Collected

### Metrics

Kubernetes Admission does not include any metrics.

### Service Checks

Kubernetes Admission does not include any service checks.

### Events

Kubernetes Admission creates `kubernetes_admission` events.

## Support

Need help? Contact [Datadog support][2].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/help/
