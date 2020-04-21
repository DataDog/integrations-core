#!/usr/bin/env python

import subprocess

from retrying import retry

# Install with TCP/IP enabled, see: https://chocolatey.org/packages/sql-server-2017


@retry(stop_max_attempt_number=2, wait_exponential_multiplier=1000)
def install_sqlserver():
    subprocess.run(["choco", "install", "sql-server-2017", "--params=\"'/TCPENABLED:1'\""], shell=True, check=True)


install_sqlserver()
