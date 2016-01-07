# Overview

Connect MySQL to Datadog in order to:

* Visualize your database performance
* Correlate the performance of MySQL with the rest of your applications

# Installation

1. Create a ```datadog``` user with replication rights in your MySQL server:

        sudo mysql -e "CREATE USER 'datadog'@'localhost' IDENTIFIED BY '<UNIQUEPASSWORD>';"
        sudo mysql -e "GRANT REPLICATION CLIENT ON *.* TO 'datadog'@'localhost' WITH MAX_USER_CONNECTIONS 5;"
2. Verify that the above commands worked by running:


        mysql -u datadog --password=<UNIQUEPASSWORD> -e "show status" | \
        grep Uptime && echo -e "\033[0;32mMySQL user - OK\033[0m" || \
        echo -e "\033[0;31mCannot connect to MySQL\033[0m"
        mysql -u datadog --password=<UNIQUEPASSWORD> -e "show slave status" && \
        echo -e "\033[0;32mMySQL grant - OK\033[0m" || \
        echo -e "\033[0;31mMissing REPLICATION CLIENT grant\033[0m"

# Configuration

1. Edit conf.d/mysql.yaml

        init_config:

        instances:
          - server: localhost
            user: datadog
            pass: <UNIQUEPASSWORD>

            tags:
                - optional_tag1
                - optional_tag2
            options:
                replication: 0
                galera_cluster: 1

2. Restart the Agent

# Validation

Execute the info command and verify that the integration check has passed. The output of the command should contain a section similar to the following:

    Checks
    ======

      [...]

      mysql
      -----
          - instance #0 [OK]
          - Collected 8 metrics & 0 events

# Compatibility
The MySQL integration is supported on versions x.x+
