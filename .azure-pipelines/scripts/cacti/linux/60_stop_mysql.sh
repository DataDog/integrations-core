#!/bin/bash

set -ex

sudo systemctl status mysql
sudo systemctl stop mysql
sudo systemctl status mysql

set +ex
