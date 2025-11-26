#!/bin/bash

set -e

clickhouse client -n <<-EOSQL
CREATE TABLE IF NOT EXISTS test
(
    id UInt64,
    updated_at DateTime DEFAULT now(),
)
ENGINE = MergeTree
ORDER BY id;
EOSQL
