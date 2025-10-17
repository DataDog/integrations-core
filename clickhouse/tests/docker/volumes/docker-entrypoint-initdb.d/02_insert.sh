#!/bin/bash

set -e

clickhouse client -n <<-EOSQL
INSERT INTO table_name VALUES (123),(456),(789);
EOSQL
