#!/usr/bin/env python

import subprocess

from retrying import retry


@retry(stop_max_attempt_number=5, wait_exponential_multiplier=1000)
def install_sqlserver():
    """
    Install with TCP/IP enabled, see: https://chocolatey.org/packages/sql-server-2017
    """
    subprocess.run(["choco", "install", "sql-server-2017", "--params=\"'/TCPENABLED:1'\""], check=True)


install_sqlserver()
