#!/bin/bash

set -e

clickhouse client -n <<-EOSQL
INSERT INTO test (id) VALUES (1),(2),(3);
EOSQL
