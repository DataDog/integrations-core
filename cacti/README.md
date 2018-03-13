# Cacti Integration

## Overview

Get metrics from cacti service in real time to:

* Visualize and monitor cacti states
* Be notified about cacti failovers and events.

## Setup
### Installation

The Cacti check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your Cacti servers.

### Configuration

Create a datadog user with read-only rights to the Cacti database

```
sudo mysql -e "create user 'datadog'@'localhost' identified by '<password>';"
sudo mysql -e "grant select on cacti.* to 'datadog'@'localhost';"
```

Check user and rights

```
mysql -u datadog --password=<password> -e "show status" | \
grep Uptime && echo -e "\033[0;32mMySQL user - OK\033[0m" || \
echo -e "\033[0;31mCannot connect to MySQL\033[0m"

mysql -u datadog --password=<password> -D cacti -e "select * from data_template_data limit 1" && \
echo -e "\033[0;32mMySQL grant - OK\033[0m" || \
echo -e "\033[0;31mMissing SELECT grant\033[0m"
```

Configure the Agent to connect to MySQL
Edit conf.d/`cacti.yaml`. See the [sample cacti.yaml](https://github.com/DataDog/integrations-core/blob/master/cacti/conf.yaml.example) for all available configuration options:

```
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

Give the dd-agent user access to the RRD files

```
sudo gpasswd -a dd-agent www-data
sudo chmod -R g+rx /var/lib/cacti/rra/
sudo su - dd-agent -c 'if [ -r /var/lib/cacti/rra/ ];
then echo -e "\033[0;31mdd-agent can read the RRD files\033[0m";
else echo -e "\033[0;31mdd-agent can not read the RRD files\033[0m";
fi'
```

### Validation

[Run the Agent's `status` subcommand](https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information) and look for `cacti` under the Checks section:

```
  Checks
  ======
    [...]

    cacti
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```

## Compatibility

The Cacti check is compatible with all major platforms

## Data Collected
### Metrics
See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/cacti/metadata.csv) for a list of metrics provided by this integration.

### Events
The Cacti check does not include any event at this time.

### Service Checks
The Cacti check does not include any service check at this time.

## Troubleshooting
Need help? Contact [Datadog Support](http://docs.datadoghq.com/help/).

## Further Reading
Learn more about infrastructure monitoring and all our integrations on [our blog](https://www.datadoghq.com/blog/)
