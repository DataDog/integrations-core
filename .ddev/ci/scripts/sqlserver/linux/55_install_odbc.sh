#!/bin/bash

set -ex

sudo apt-get update
sudo apt-get install -y --no-install-recommends tdsodbc unixodbc-dev

# Install the Microsoft ODBC driver for SQL Server (Linux)
curl https://packages.microsoft.com/keys/microsoft.asc | sudo tee /etc/apt/trusted.gpg.d/microsoft.asc
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18

set +ex
