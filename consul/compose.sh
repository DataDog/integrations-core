#!/bin/bash

export CONSUL_VERSION=v0.6.4
# CONSUL_VERSION=0.7.2
# CONSUL_VERSION=1.0.0
# CONSUL_VERSION=1.0.6

export CONSUL_CONFIG_PATH="./tests/compose/server-$CONSUL_VERSION.json"
export CONSUL_PORT='8500'

docker-compose -f tests/compose/compose.yaml up -d
