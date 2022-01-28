# Agent Check: terraform

## Overview

The Datadog Terraform provider allows you to interact with the Datadog API through a Terraform configuration. You can manage your Datadog resources, such as Dashboards, Monitors, Logs Configuration, etc, with this configuration.

## Setup

### Installation

The Datadog Terraform provider is available through the [Terraform Registry][1].

### Configuration

1. [Install Terraform][2]
2. Create a directory to contain the Terraform configuration files, for example: `terraform_config/`
3. Create a `main.tf` file in the `terraform_config/` directory with the following content:
    ```
    terraform {
      required_providers {
        datadog = {
          source = "DataDog/datadog"
        }
      }
    }

    # Configure the Datadog provider
    provider "datadog" {
      api_key = var.datadog_api_key
      app_key = var.datadog_app_key
    }
    ```

4. Run `terraform init`. This initializes the directory for use with Terraform and pulls the Datadog provider.
5. Create any `.tf` file in the `terraform_config/` directory and start creating Datadog resources. For example:

    ```
    # monitor.tf
    resource "datadog_monitor" "process_alert_example" {
      name    = "Process Alert Monitor"
      type    = "process alert"
      message = "Multiple Java processes running on example-tag"
      query   = "processes('java').over('example-tag').rollup('count').last('10m') > 1"
      monitor_thresholds {
        critical          = 1.0
        critical_recovery = 0.0
      }

      notify_no_data    = false
      renotify_interval = 60
    }
    ```

6. Run `terraform apply` to create this monitor in your Datadog account!

## Data Collected

### Metrics

Terraform does not include any metrics.

### Service Checks

Terraform does not include any service checks.

### Events

Terraform does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://registry.terraform.io/providers/DataDog/datadog/latest/docs
[2]: https://learn.hashicorp.com/tutorials/terraform/install-cli
[3]: https://docs.datadoghq.com/help/
