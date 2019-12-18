CREATE TABLE tableau (id Int64) ENGINE = ReplicatedMergeTree('/clickhouse/tables/{layer}-{shard}/tableau', '{replica}') PARTITION BY id ORDER BY id;
CREATE TABLE tableau_distributed as tableau ENGINE = Distributed(cluster_1, default, tableau, rand());
INSERT INTO tableau VALUES (123),(456),(789);
