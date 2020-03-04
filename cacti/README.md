# Cacti Integration

## Overview

Get metrics from Cacti in real time to:

- Visualize and monitor Cacti states.
- Be notified about Cacti failovers and events.

## Setup

### Installation

The Cacti check is included in the [Datadog Agent][1] package, to start gathering metrics you first need to:

1. Install `librrd` headers and libraries.
2. Install python bindings to `rrdtool`.

#### librrd headers and librairies

On Debian/Ubuntu:

```shell
sudo apt-get install librrd-dev
```

On RHEL/CentOS:

```shell
sudo yum install rrdtool-devel
```

#### Python bindings

Now add the `rrdtool` Python package to the Agent with the following command:

```shell
sudo -u dd-agent /opt/datadog-agent/embedded/bin/pip install rrdtool
```

### Configuration

#### Create a Datadog user

1. Create a Datadog user with read-only rights to the Cacti database.

   ```shell
   sudo mysql -e "create user 'datadog'@'localhost' identified by '<MYSQL_PASSWORD>';"
   sudo mysql -e "grant select on cacti.* to 'datadog'@'localhost';"
   ```

2. Check the user and rights:

   ```shell
   mysql -u datadog --password=<MYSQL_PASSWORD> -e "show status" | \
   grep Uptime && echo -e "\033[0;32mMySQL user - OK\033[0m" || \
   echo -e "\033[0;31mCannot connect to MySQL\033[0m"

   mysql -u datadog --password=<MYSQL_PASSWORD> -D cacti -e "select * from data_template_data limit 1" && \
   echo -e "\033[0;32mMySQL grant - OK\033[0m" || \
   echo -e "\033[0;31mMissing SELECT grant\033[0m"
   ```

3. Give the `datadog-agent` user access to the RRD files:

   ```shell
   sudo gpasswd -a dd-agent www-data
   sudo chmod -R g+rx /var/lib/cacti/rra/
   sudo su - datadog-agent -c 'if [ -r /var/lib/cacti/rra/ ];
   then echo -e "\033[0;31mdatadog-agent can read the RRD files\033[0m";
   else echo -e "\033[0;31mdatadog-agent can not read the RRD files\033[0m";
   fi'
   ```

#### Configure the Agent

1. Configure the Agent to connect to MySQL, edit your `cacti.d/conf.yaml` file. See the [sample cacti.d/conf.yaml][2] for all available configuration options:

   ```yaml
   init_config:

   instances:
     ## @param mysql_host - string - required
     ## url of your MySQL database
     #
     - mysql_host: "localhost"

       ## @param mysql_port - integer - optional - default: 3306
       ## port of your MySQL database
       #
       # mysql_port: 3306

       ## @param mysql_user - string - required
       ## User to use to connect to MySQL in order to gather metrics
       #
       mysql_user: "datadog"

       ## @param mysql_password - string - required
       ## Password to use to connect to MySQL in order to gather metrics
       #
       mysql_password: "<MYSQL_PASSWORD>"

       ## @param rrd_path - string - required
       ## The Cacti checks requires access to the Cacti DB in MySQL and to the RRD
       ## files that contain the metrics tracked in Cacti.
       ## In almost all cases, you'll only need one instance pointing to the Cacti
       ## database.
       ## The `rrd_path` will probably be `/var/lib/cacti/rra` on Ubuntu
       ## or `/var/www/html/cacti/rra` on any other machines.
       #
       rrd_path: "<CACTI_RRA_PATH>"
   ```

2. [Restart the Agent][3].

### Validation

[Run the Agent's status subcommand][4] and look for `cacti` under the Checks section.

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

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://github.com/DataDog/integrations-core/blob/master/cacti/datadog_checks/cacti/data/conf.yaml.example
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://github.com/DataDog/integrations-core/blob/master/cacti/metadata.csv
[6]: https://github.com/pbanaszkiewicz/python-rrdtool
[7]: https://github.com/commx/python-rrdtool/issues/25
[8]: https://docs.datadoghq.com/help
