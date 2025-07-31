CREATE TABLE IF NOT EXISTS table_name (
    id UInt32
) ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/table_name', '{replica}')
PARTITION BY id
ORDER BY id;

INSERT INTO table_name VALUES (123),(456),(789);
