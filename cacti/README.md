# Cacti Integration

## Overview

Get metrics from cacti service in real time to:

* Visualize and monitor cacti states
* Be notified about cacti failovers and events.

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][1] for guidance on applying these instructions.

### Installation

The Cacti check is included in the [Datadog Agent][2] package, to start gathering metrics you first need to:
- Install librrd headers and libraries
- Install python bindings to rrdtool

#### librrd headers and librairies

On Debian/Ubuntu
```shell
sudo apt-get install librrd-dev
```

On RHEL/CentOS
```shell
sudo yum install rrdtool-devel
```

#### Python bindinges

Now add the `rrdtool` Python package to the Agent with the following command.
```shell
sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install rrdtool
```

### Configuration

Create a datadog user with read-only rights to the Cacti database

```shell
sudo mysql -e "create user 'datadog'@'localhost' identified by '<password>';"
sudo mysql -e "grant select on cacti.* to 'datadog'@'localhost';"
```

Check user and rights

```shell
mysql -u datadog --password=<password> -e "show status" | \
grep Uptime && echo -e "\033[0;32mMySQL user - OK\033[0m" || \
echo -e "\033[0;31mCannot connect to MySQL\033[0m"

mysql -u datadog --password=<password> -D cacti -e "select * from data_template_data limit 1" && \
echo -e "\033[0;32mMySQL grant - OK\033[0m" || \
echo -e "\033[0;31mMissing SELECT grant\033[0m"
```

Configure the Agent to connect to MySQL, edit your `cacti.d/conf.yaml` file. See the [sample cacti.d/conf.yaml][3] for all available configuration options:

```yaml
init_config:

instances:
    -   mysql_host: localhost
        mysql_user: datadog
        mysql_password: hx3beOpMFcvxn9gXcs0MU3jX
        rrd_path: /path/to/cacti/rra
        #field_names:
        #    - ifName
        #    - dskDevice
        #    - ifIndex
        #rrd_whitelist: /path/to/rrd_whitelist.txt
```

Give the datadog-agent user access to the RRD files

```shell
sudo gpasswd -a dd-agent www-data
sudo chmod -R g+rx /var/lib/cacti/rra/
sudo su - datadog-agent -c 'if [ -r /var/lib/cacti/rra/ ];
then echo -e "\033[0;31mdatadog-agent can read the RRD files\033[0m";
else echo -e "\033[0;31mdatadog-agent can not read the RRD files\033[0m";
fi'
```

### Validation

[Run the Agent's `status` subcommand][4] and look for `cacti` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][5] for a list of metrics provided by this integration.

### Events
The Cacti check does not include any events.

### Service Checks
The Cacti check does not include any service checks.

## Troubleshooting
### Known issues
The Python library used by this integration leaks memory under certain circumstances. If you experience this, one workaround is to install the [python-rrdtool][6] package instead of rrdtool. This older package is not maintained and is not officially supported by this integration but it has helped others resolve the memory issues.

A [Github issue][7] has been opened to track this memory leak.

Need help? Contact [Datadog support][8].

[1]: https://docs.datadoghq.com/agent/autodiscovery/integrations
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/cacti/datadog_checks/cacti/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/cacti/metadata.csv
[6]: https://github.com/pbanaszkiewicz/python-rrdtool
[7]: https://github.com/commx/python-rrdtool/issues/25
[8]: https://docs.datadoghq.com/help
