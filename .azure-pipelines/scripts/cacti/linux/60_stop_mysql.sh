#!/bin/bash

set -ex

# E2E test need port 3060, hence we need to stop the mysql server provided by Azure Pipelines
sudo systemctl stop mysql

set +ex
