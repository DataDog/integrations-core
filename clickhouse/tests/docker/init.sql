CREATE TABLE IF NOT EXISTS tableau (id Int64) ENGINE = ReplicatedMergeTree('/clickhouse/tables/{layer}-{shard}/tableau', '{replica}') PARTITION BY id ORDER BY id;
CREATE TABLE IF NOT EXISTS tableau_distributed as tableau ENGINE = Distributed(cluster_1, default, tableau, rand());
INSERT INTO tableau VALUES (123),(456),(789);
ALTER USER default SETTINGS async_insert=1;
INSERT INTO tableau SETTINGS async_insert=1, wait_for_async_insert=2 VALUES (111),(222),(333);
