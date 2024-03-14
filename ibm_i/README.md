# Agent Check: IBM i

## Overview

This check monitors [IBM i][1] remotely through the Datadog Agent.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

**Note**: This check is not available on Windows as it uses the `fcntl()` system call, which is specific to Unix-like operating systems.

### Installation

The IBM i check is included in the [Datadog Agent][3] package.
No additional installation is needed on your server.

#### ODBC driver

The IBM i check uses the IBM i ODBC driver to connect remotely to the IBM i host. 

Download the driver from the [IBM i Access - Client Solutions][4] page. Click on `Downloads for IBM i Access Client Solutions` and login to gain access to the downloads page.

Choose the `ACS App Pkg` package for your platform, such as `ACS Linux App Pkg` for Linux hosts. Download the package and follow the installation instructions to install the driver.

### Configuration

The IBM i check queries an IBM i system remotely from a host running the Datadog Agent. To communicate with the IBM i system, you need to set up the IBM i ODBC driver on the host running the Datadog Agent.

#### ODBC driver

Once the ODBC driver is installed, find the ODBC configuration files: `odbc.ini` and `odbcinst.ini`. The location may vary depending on your system. On Linux they may be located in the `/etc` directory or in the `/etc/unixODBC` directory.

Copy these configuration files to the embedded Agent environment, such as `/opt/datadog-agent/embedded/etc/` on Linux hosts.

The `odbcinst.ini` file defines the available ODBC drivers for the Agent. Each section defines one driver. For instance, the following section defines a driver named `IBM i Access ODBC Driver 64-bit`:
```
[IBM i Access ODBC Driver 64-bit]
Description=IBM i Access for Linux 64-bit ODBC Driver
Driver=/opt/ibm/iaccess/lib64/libcwbodbc.so
Setup=/opt/ibm/iaccess/lib64/libcwbodbcs.so
Threading=0
DontDLClose=1
UsageCount=1
```

The name of the IBM i ODBC driver is needed to configure the IBM i check.

#### IBM i check

1. Edit the `ibm_i.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your IBM i performance data. See the [sample ibm_i.d/conf.yaml][5] for all available configuration options.
   Use the driver name from the `obdcinst.ini` file.

2. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][7] and look for `ibm_i` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][8] for a list of metrics provided by this check.

### Service Checks

See [service_checks.json][9] for a list of service checks provided by this integration.

### Events

The IBM i check does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://www.ibm.com/it-infrastructure/power/os/ibm-i
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://www.ibm.com/support/pages/ibm-i-access-client-solutions
[5]: https://github.com/DataDog/integrations-core/blob/master/ibm_i/datadog_checks/ibm_i/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[8]: https://github.com/DataDog/integrations-core/blob/master/ibm_i/metadata.csv
[9]: https://github.com/DataDog/integrations-core/blob/master/ibm_i/datadog_checks/ibm_i/assets/service_checks.json
[10]: https://docs.datadoghq.com/help/
