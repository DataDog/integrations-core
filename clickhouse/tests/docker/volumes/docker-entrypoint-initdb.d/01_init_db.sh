#!/bin/bash

set -e

clickhouse client -n <<-EOSQL
CREATE TABLE IF NOT EXISTS test
(
    id UInt64,
    updated_at DateTime DEFAULT now()
)
ENGINE = ReplicatedMergeTree('/clickhouse/tables/test', '{replica}')
PARTITION BY id
ORDER BY id;
EOSQL
