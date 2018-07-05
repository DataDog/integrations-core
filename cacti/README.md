# Cacti Integration

## Overview

Get metrics from cacti service in real time to:

* Visualize and monitor cacti states
* Be notified about cacti failovers and events.

## Setup
### Installation

The Cacti check is included in the [Datadog Agent][1] package, so you don't need to install anything else on your Cacti servers.

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

Configure the Agent to connect to MySQL, edit your `cacti.d/conf.yaml` file. See the [sample cacti.d/conf.yaml][2] for all available configuration options:

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

[Run the Agent's `status` subcommand][3] and look for `cacti` under the Checks section.

## Data Collected
### Metrics
See [metadata.csv][4] for a list of metrics provided by this integration.

### Events
The Cacti check does not include any events at this time.

### Service Checks
The Cacti check does not include any service checks at this time.

## Troubleshooting
Need help? Contact [Datadog Support][5].

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/cacti/datadog_checks/cacti/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[4]: https://github.com/DataDog/integrations-core/blob/master/cacti/metadata.csv
[5]: https://docs.datadoghq.com/help/
