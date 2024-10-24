# Agent Check: Kubernetes Audit Webhook

## Overview

Kubernetes Audit Webhook will generate pseudo-Audit events for Kubernetes.

The Kubernetes Audit Webhook for Datadog's Cluster Agent offers an easy-to-deploy solution for tracking and monitoring Kubernetes API activity. 
By sending real-time Datadog events for every request, it provides comprehensive visibility and enhances security, all without the complexity of setting up Kubernetes Audit Logs.

## Setup

### Installation

The Kubernetes Audit Webhook check is included in the [Datadog Agent][1] package.
No additional installation is needed on your server.

### Configuration

You can activate this feature by activating the `admission_controller_kubernetes_audit_webhook` setting.

### Validation

!!! Add steps to validate integration is functioning as expected !!!

## Data Collected

### Metrics

Kubernetes Audit Webhook does not include any metrics.

### Service Checks

Kubernetes Audit Webhook does not include any service checks.

### Events

Kubernetes Audit Webhook creates `kubernetes_audit` events.

## Troubleshooting

Need help? Contact [Datadog support][2].

[1]: https://app.datadoghq.com/account/settings/agent/latest
[2]: https://docs.datadoghq.com/help/

