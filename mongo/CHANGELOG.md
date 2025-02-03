# CHANGELOG - mongo

<!-- towncrier release notes start -->

## 8.4.0 / 2025-01-25

***Added***:

* Add support for `zlib` network compression in the MongoDB integration client with fallback to uncompressed connections. ([#19395](https://github.com/DataDog/integrations-core/pull/19395))
* Make MongoDB Atlas search indexes collection configurable and disable it by default for improved performance. ([#19396](https://github.com/DataDog/integrations-core/pull/19396))
* Increased the default collection interval for MongoDB inferred schema and index definitions to 1 hour to reduce resource overhead. ([#19445](https://github.com/DataDog/integrations-core/pull/19445))
* Include explain operations in MongoDB activity samples. ([#19450](https://github.com/DataDog/integrations-core/pull/19450))
* Add `service=datadog-agent` comment to MongoDB integration operations for tagging integration operations. ([#19456](https://github.com/DataDog/integrations-core/pull/19456))

***Fixed***:

* Fix error `CommandCursor is not subscriptable` in replication oplog size and oplog window collection. ([#19444](https://github.com/DataDog/integrations-core/pull/19444))

## 8.3.1 / 2024-12-26 / Agent 7.62.0

***Fixed***:

* Skip unauthorized `local` database collections `system.replset`, `replset.election`, and `replset.minvalid` in collection and index stats gathering to avoid permission errors. ([#19244](https://github.com/DataDog/integrations-core/pull/19244))

## 8.3.0 / 2024-11-28 / Agent 7.61.0

***Added***:

* Add `metrics_collection_interval` config option to customize the collection interval for collection stats, index stats, and sharded data distribution metrics.
  The default collection interval for collection stats and index stats remains unchanged at check min collection interval of 15 seconds.
  The default collection interval for sharded data distribution metrics is 300 seconds. ([#19098](https://github.com/DataDog/integrations-core/pull/19098))

***Fixed***:

* Fixes timezone parsing bug in slow query log, preventing incorrect timestamp conversions on non-UTC servers. ([#19057](https://github.com/DataDog/integrations-core/pull/19057))
* Fix crash in DBM operation samples collection when a node is in recovering mode. ([#19080](https://github.com/DataDog/integrations-core/pull/19080))
* Resolved deprecation warning for `collStats` by using `$collStats` aggregation pipeline to collect oplog size in MongoDB 6.2+. ([#19133](https://github.com/DataDog/integrations-core/pull/19133))

## 8.2.1 / 2024-11-06 / Agent 7.60.0

***Fixed***:

* Fix bug in parsing database name from namespace when no collection name is present, affecting database-level commands in MongoDB versions 5 and earlier. ([#18953](https://github.com/DataDog/integrations-core/pull/18953))

## 8.2.0 / 2024-10-31

***Added***:

* Add `service` configured in integration init_config or instance config to the DBM events payload. The configured `service` will be converted to tag `service:<SERVICE>` and applied, query samples, slow queries and explain plans. ([#18846](https://github.com/DataDog/integrations-core/pull/18846))
* Add `aws` to the instance configuration to allow cloud resource linking with Amazon DocumentDB. ([#18921](https://github.com/DataDog/integrations-core/pull/18921))

***Fixed***:

* Skip explain plan collection for mongo administrative aggregation pipeline, including `$collStats`, `$currentOp`, `$indexStats`, `$listSearchIndexes`, `$sample` and `$shardedDataDistribution`. ([#18844](https://github.com/DataDog/integrations-core/pull/18844))

## 8.1.0 / 2024-10-16 / Agent 7.59.0

***Added***:

* Apply `timeoutMS` to integration connection to ensure client-side operation timeouts terminate the server processes. ([#18843](https://github.com/DataDog/integrations-core/pull/18843))

## 8.0.0 / 2024-10-04

***Removed***:

* Remove support for Python 2. ([#18580](https://github.com/DataDog/integrations-core/pull/18580))
* Bump datadog-checks-base dependency ([#18583](https://github.com/DataDog/integrations-core/pull/18583))
* Add `mongodb.system.cpu.percent` metric to track total CPU usage of the MongoDB process on self-hosted instances (only available on self-hosted MongoDB running on the same host as the Agent). ([#18618](https://github.com/DataDog/integrations-core/pull/18618))
* Always emit `database_instance` metadata regardless of DBM status; previously emitted only when DBM was enabled. ([#18750](https://github.com/DataDog/integrations-core/pull/18750))
* Include tag `clustername` & `database_instance` in mongo service check tags ([#18751](https://github.com/DataDog/integrations-core/pull/18751))
* Add `resolved_views`, `working_millis`, and `queues` fields to the slow query (dbm only) event payload
  - resolved_views: contains view details for slow queries on views (MongoDB 5.0+)
  - working_millis: the amount of time that MongoDB spends working on the operation (MongoDB 8.0+)
  - queues: contains information about the operation's queues (MongoDB 8.0+) ([#18761](https://github.com/DataDog/integrations-core/pull/18761))

## 7.0.0 / 2024-10-01 / Agent 7.58.0

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump the python version from 3.11 to 3.12 ([#18212](https://github.com/DataDog/integrations-core/pull/18212))
* Upgrade psutil to 6.0.0 to fix performance issues addressed ([#18688](https://github.com/DataDog/integrations-core/pull/18688))

## 6.11.0 / 2024-09-10

***Added***:

* Add `index` tag to `mongodb.collection.indexes.accesses.opsps` metric for consistency with `mongodb.collection.indexsizes`. ([#18546](https://github.com/DataDog/integrations-core/pull/18546))

## 6.10.0 / 2024-09-05

***Deprecated***:

* Deprecate metrics `mongodb.collection.collectionscans.nontailable` & `mongodb.collection.collectionscans.total`. ([#18511](https://github.com/DataDog/integrations-core/pull/18511))

***Added***:

* Collecting Explain Plans for Slow Operations:
  - For slow operations captured by the database profiler, the `execStats` from the profiler documents are directly used and emitted.
  - For slow operations identified in the logs, the integration now explicitly explains the operation and emits the resulting explain plan. ([#18309](https://github.com/DataDog/integrations-core/pull/18309))
* Add metric `mongodb.stats.views` to report number of views in the database. ([#18334](https://github.com/DataDog/integrations-core/pull/18334))
* Collect mongodb inferred document schema with documents sample (DBM only). By default, 10 documents per collection are sampled to generate inferred schema with fields and types. ([#18374](https://github.com/DataDog/integrations-core/pull/18374))
* Add `query_framework` to operation samples. `query_framework` is a string that specifies the query framework used to process an operation. The field is available starting mongodb version 6.2. ([#18388](https://github.com/DataDog/integrations-core/pull/18388))
* Add metric `mongodb.collection.indexes.accesses.opsps` to measure number of times the index was used per second. ([#18405](https://github.com/DataDog/integrations-core/pull/18405))
* Add sharded data distribution metrics (only collected on mongos)
  - `mongodb.sharded_data_distribution.num_orphaned_docs`, - Number of orphaned documents in the shard
  - `mongodb.sharded_data_distribution.num_owned_documents` - Number of owned documents in the shard
  - `mongodb.sharded_data_distribution.orphaned_size_bytes` - Size of orphaned documents in the shard
  - `mongodb.sharded_data_distribution.owned_size_bytes` - Size of owned documents in the shard ([#18407](https://github.com/DataDog/integrations-core/pull/18407))
* Improve MongoDB integration compatibility with AWS DocumentDB
  - fallback to `collStats` command when `$collStats` aggregation pipeline is not available
  - fix NoneType error with replication metrics collection
  - fix `list_collection_names` error on unsupported filter `Type` ([#18430](https://github.com/DataDog/integrations-core/pull/18430))
* Include replica set tags in metrics. ([#18463](https://github.com/DataDog/integrations-core/pull/18463))
* Add modules to mongodb instance metadata. `modules` are a list of add-on modules that mongod was built with. Possible values currently include "enterprise" and "rocksdb". ([#18473](https://github.com/DataDog/integrations-core/pull/18473))
* Collect MongoDB Atlas search indexes in schema collection (DBM only). ([#18476](https://github.com/DataDog/integrations-core/pull/18476))
* Update dependencies ([#18478](https://github.com/DataDog/integrations-core/pull/18478))
* Obfuscate literal values within the `parsedQuery`, `filter`, and `indexBounds` fields in MongoDB explain plans. ([#18499](https://github.com/DataDog/integrations-core/pull/18499))
* Enables MongoDB inferred schema collection by default (DBM only). ([#18502](https://github.com/DataDog/integrations-core/pull/18502))
* Add warning logs when agent user is not authorized to run $collStats and $indexStats on collections. ([#18506](https://github.com/DataDog/integrations-core/pull/18506))
* Emit new metrics `mongodb.collection.collectionscans.totalps` & `mongodb.collection.collectionscans.nontailableps`. The new metrics measure the total number of queries that performed a collection scans or collection scans without tailable cursor per second. ([#18511](https://github.com/DataDog/integrations-core/pull/18511))
* Add new metrics for MongoDB query plan cache (requires MongoDB 7.0+) and sort stages (requires MongoDB 6.2+):
  - mongodb.metrics.query.plancache.classic.hitsps
  - mongodb.metrics.query.plancache.classic.missesps
  - mongodb.metrics.query.plancache.sbe.hitsps
  - mongodb.metrics.query.plancache.sbe.missesps
  - mongodb.metrics.query.sort.spilltodiskps
  - mongodb.metrics.query.sort.totalbytessortedps
  - mongodb.metrics.query.sort.totalkeyssortedps ([#18513](https://github.com/DataDog/integrations-core/pull/18513))

***Fixed***:

* Remove `comment` from obfuscate command and send it as a separate field in operation samples and slow operations payload. ([#18404](https://github.com/DataDog/integrations-core/pull/18404))
* Cache database profiling level to avoid repeated queries in slow operations sampling. ([#18461](https://github.com/DataDog/integrations-core/pull/18461))

## 6.9.0 / 2024-08-27 / Agent 7.57.0

***Added***:

* Add config option `database_autodiscovery.max_collections_per_database` to limit max number of collections to be monitored per autodiscoverd database. This option is applied to collection stats metrics and collection indexes stats metrics. ([#18416](https://github.com/DataDog/integrations-core/pull/18416))

***Fixed***:

* Skip collect explain plan for get profile level & listCollections command. ([#18408](https://github.com/DataDog/integrations-core/pull/18408))

## 6.8.2 / 2024-08-16

***Fixed***:

* Fixed a bug where optional MongoDB collection stats metrics were always collected, regardless of configuration. ([#18342](https://github.com/DataDog/integrations-core/pull/18342))

## 6.8.1 / 2024-08-13

***Fixed***:

* Fix missing metrics `num_yields` and `response_length` for slow operations collected from logs. ([#18305](https://github.com/DataDog/integrations-core/pull/18305))

## 6.8.0 / 2024-08-09

***Added***:

* Collects 3 additional WiredTiger cache metrics from serverStatus
  - wiredtiger.cache.bytes_read_into_cache
  - wiredtiger.cache.bytes_written_from_cache
  - wiredtiger.cache.pages_requested_from_cache ([#18052](https://github.com/DataDog/integrations-core/pull/18052))
* Collect MongoDB slow operations for auto-discovered databases when DBM is enabled. The slow operations are collected from
  - `system.profile` collection when database profiler is enabled
  - MongoDB slow query logs when database profiler is not enabled ([#18140](https://github.com/DataDog/integrations-core/pull/18140))
* Add `hosting_type` tag to the Mongo metrics. This tag indicates where the MongoDB instance is hosted. ([#18167](https://github.com/DataDog/integrations-core/pull/18167))
* Add database and collection level average latency metrics by operation type
  - mongodb.oplatencies.commands.latency.avg
  - mongodb.oplatencies.reads.latency.avg
  - mongodb.oplatencies.writes.latency.avg
  - mongodb.collection.commands.latency.avg
  - mongodb.collection.reads.latency.avg
  - mongodb.collection.transactions.latency.avg
  - mongodb.collection.writes.latency.avg ([#18177](https://github.com/DataDog/integrations-core/pull/18177))
* Introduced a new `HostInfo` metrics collector to gather system-level metrics for the host running the `mongod` or `mongos` process. The following metrics are now collected by default across all deployment types:
  - `mongodb.system.cpu.cores`
  - `mongodb.system.mem.limit`
  - `mongodb.system.mem.total` ([#18196](https://github.com/DataDog/integrations-core/pull/18196))
* Add new database storage metrics collected from `dbStats`. The new metrics include
  - mongodb.stats.freestoragesize
  - mongodb.stats.fstotalsize
  - mongodb.stats.fsusedsize
  - mongodb.stats.indexfreestoragesize
  - mongodb.stats.totalfreestoragesize
  - mongodb.stats.totalsize ([#18200](https://github.com/DataDog/integrations-core/pull/18200))
* Collect operation samples (DBM only) for operations that run on system databases (e.g. admin, local, config). ([#18224](https://github.com/DataDog/integrations-core/pull/18224))

***Fixed***:

* Fix the default null value for waiting_for_latch in operation sampling. When an operation is not waiting for latch, waiting_for_latch should be an empty dict instead of boolean False. ([#17997](https://github.com/DataDog/integrations-core/pull/17997))
* Fix connection error `SCRAM-SHA-256 requires a username` when connection option authMechanism is provided ([#18156](https://github.com/DataDog/integrations-core/pull/18156))

## 6.7.2 / 2024-07-19 / Agent 7.56.0

***Fixed***:

* Rename dbms from `mongodb` to `mongo` so that dbms is consistent with integration name. ([#18067](https://github.com/DataDog/integrations-core/pull/18067))

## 6.7.1 / 2024-07-17

***Fixed***:

* Fix coll or index stats metrics failure when the agent user is not authorized to perform $collStats or $indexStats aggregation on a collection. This fix prevents check to fail when an OperationFailure is raised to run $collStats or $indexStats on system collections such as system.replset on local database. ([#18044](https://github.com/DataDog/integrations-core/pull/18044))

## 6.7.0 / 2024-07-05

***Deprecated***:

* Configuration option `dbnames` is deprecated and will be removed in a future release.
  To monitor multiple databases, set `database_autodiscovery.enabled` to true and configure `database_autodiscovery.include` and `database_autodiscovery.exclude` filters instead. ([#17959](https://github.com/DataDog/integrations-core/pull/17959))

***Added***:

* Add config option to use reported_database_hostname to override the mongodb instance hostname detected from admin command serverStatus.host ([#17800](https://github.com/DataDog/integrations-core/pull/17800))
* Update dependencies ([#17817](https://github.com/DataDog/integrations-core/pull/17817)), ([#17953](https://github.com/DataDog/integrations-core/pull/17953))
* Add new `replset_me` tag to mongodb instances that belong to a replica set ([#17829](https://github.com/DataDog/integrations-core/pull/17829))
* Add cursor object to sampled activities and explain plan payload. cursor contains the cursor information for idleCursor and getmore operations. ([#17840](https://github.com/DataDog/integrations-core/pull/17840))
* Add tag `clustername` to mongo metrics. This tag is set only when `cluster_name` is provided in the integration configuration. ([#17876](https://github.com/DataDog/integrations-core/pull/17876))
* Update mongo conf.yaml.example to include DBM for MongoDB config options. The new config options includes `dbm`, `cluster_name`, `operation_samples.enabled` & `operation_samples.collection_interval`. ([#17940](https://github.com/DataDog/integrations-core/pull/17940))
* Support auto-discover available databases (up to 100 databases) for the monitored mongodb instance. 
  By default, database autodiscovery is disabled. Set `database_autodiscovery.enabled` to true to enable database autodiscovery. 
  When enabled, the integration will automatically discover the databases available in the monitored mongodb instance and refresh the list of databases every 10 minutes.
  Use `database_autodiscovery.include` and `database_autodiscovery.exclude` to filter the list of databases to monitor. ([#17959](https://github.com/DataDog/integrations-core/pull/17959))
* Added new collection latency and query execution stats metrics.
  - mongodb.collection.totalindexsize
  - mongodb.collection.collectionscans.nontailable
  - mongodb.collection.collectionscans.total
  - mongodb.collection.commands.latency
  - mongodb.collection.commands.opsps
  - mongodb.collection.reads.latency
  - mongodb.collection.reads.opsps
  - mongodb.collection.transactions.latency
  - mongodb.collection.transactions.opsps
  - mongodb.collection.writes.latency
  - mongodb.collection.writes.opsps ([#17961](https://github.com/DataDog/integrations-core/pull/17961))

***Fixed***:

* Excludes keys `'readConcern', 'writeConcern', 'needsMerge', 'fromMongos', 'let', 'mayBypassWriteBlocking'` from sampled commands that cause explain to fail ([#17836](https://github.com/DataDog/integrations-core/pull/17836))
* Replace deprecated collStats command with $collStats aggregation stage to collect collection metrics ([#17961](https://github.com/DataDog/integrations-core/pull/17961))

## 6.6.0 / 2024-06-13

***Added***:

* Include namespace in DBM samples operation_metadata ([#17730](https://github.com/DataDog/integrations-core/pull/17730))
* Add support for AWS DocumentDB Instance-Based Clusters ([#17779](https://github.com/DataDog/integrations-core/pull/17779))
* Always collect database stats from replicaset primaries ([#17798](https://github.com/DataDog/integrations-core/pull/17798))

***Fixed***:

* Skip emitting mongodb samples on unexplainable operations ([#17785](https://github.com/DataDog/integrations-core/pull/17785))

## 6.5.0 / 2024-05-31 / Agent 7.55.0

***Added***:

* Emit mongodb_instance metadata event to for sharded cluster, replica-set and standalone deployment types. The metadata includes
  - mongodb hostname
  - mongodb version
  - replica set name
  - replica set state
  - sharding cluster role
  - cluster type
  - hosts (list of mongodb instances this mongodb connects to)
  - shards (list of shards this mongos instance connects to)
  - cluster name ([#17518](https://github.com/DataDog/integrations-core/pull/17518))
* Update dependencies ([#17519](https://github.com/DataDog/integrations-core/pull/17519))
* Emit updated mongodb_instance event when mongo deployment type is refreshed with updates. The mongo deployment type is considered to be updated when
  - replica set name is changed
  - member role is updated in a replica set, i.e. primary step down/secondary step up or new member joins the replica set
  - new shard joins a sharded cluster or new member joins a shard results in mongos shard map updated ([#17564](https://github.com/DataDog/integrations-core/pull/17564))
* Samples MongoDB operations and collect explain plans for the sampled operations when DBM is enabled. ([#17596](https://github.com/DataDog/integrations-core/pull/17596))
* Bump datadog-checks-base dependency to 36.7.0 ([#17688](https://github.com/DataDog/integrations-core/pull/17688))

***Fixed***:

* Emit database_instance metadata before collecting metrics ([#17665](https://github.com/DataDog/integrations-core/pull/17665))
* Only emit database_instance metadata when dbm is enabled ([#17697](https://github.com/DataDog/integrations-core/pull/17697))

## 6.4.0 / 2024-04-26 / Agent 7.54.0

***Added***:

* Add flag to exclude `db` tag from dbstats metrics ([#17276](https://github.com/DataDog/integrations-core/pull/17276))
* Add host tags triggered events ([#17287](https://github.com/DataDog/integrations-core/pull/17287))
* Update dependencies ([#17319](https://github.com/DataDog/integrations-core/pull/17319))

## 6.3.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Update dependencies ([#16963](https://github.com/DataDog/integrations-core/pull/16963))

## 6.2.0 / 2024-02-16 / Agent 7.52.0

***Added***:

* Bump `pymongo` version to 4.6.1 ([#16554](https://github.com/DataDog/integrations-core/pull/16554))

## 6.1.0 / 2024-01-05 / Agent 7.51.0

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))

***Fixed***:

* Fix fsynclocked metric ([#16525](https://github.com/DataDog/integrations-core/pull/16525))

## 6.0.2 / 2023-11-10 / Agent 7.50.0

***Fixed***:

* Handle mongodb versions with suffixes. ([#16181](https://github.com/DataDog/integrations-core/pull/16181))

## 6.0.1 / 2023-08-18 / Agent 7.48.0

***Fixed***:

* Bump base check version to 32.7.0 ([#15584](https://github.com/DataDog/integrations-core/pull/15584))

## 6.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Add a diagnostic for TLS certificate files ([#15470](https://github.com/DataDog/integrations-core/pull/15470))
* Submit critical service check whenever connection fails ([#15208](https://github.com/DataDog/integrations-core/pull/15208))
* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 5.1.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))

***Fixed***:

* Update mongo default config for multihost ([#13454](https://github.com/DataDog/integrations-core/pull/13454))
* Downgrade requirements to 3.8 ([#14711](https://github.com/DataDog/integrations-core/pull/14711))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))
* Add debug logs ([#14626](https://github.com/DataDog/integrations-core/pull/14626))

## 5.0.1 / 2023-05-26 / Agent 7.46.0

***Fixed***:

* Explicitly disallow setting `replicaSet` in the options ([#13887](https://github.com/DataDog/integrations-core/pull/13887))

## 5.0.0 / 2023-03-03 / Agent 7.44.0

***Changed***:

* remove ssl params from mongo integration ([#13881](https://github.com/DataDog/integrations-core/pull/13881))

***Added***:

* Mongo Date types support in custom queries ([#13516](https://github.com/DataDog/integrations-core/pull/13516))

***Fixed***:

* Exception is thrown when items of a list in a custom query are not iterable ([#13895](https://github.com/DataDog/integrations-core/pull/13895))

## 4.3.0 / 2023-02-07 / Agent 7.43.0

***Fixed***:

* Exception is thrown when items of a list in a custom query are not iterable ([#13895](https://github.com/DataDog/integrations-core/pull/13895))

## 4.2.0 / 2023-02-01

***Added***:

* Mongo Date types support in custom queries ([#13516](https://github.com/DataDog/integrations-core/pull/13516))

## 4.1.2 / 2023-01-20

***Fixed***:

* Update dependencies ([#13726](https://github.com/DataDog/integrations-core/pull/13726))
* Skip checking database names when replica is recovering ([#13535](https://github.com/DataDog/integrations-core/pull/13535))

## 4.1.1 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Stop using deprecated `distutils.version` classes ([#13408](https://github.com/DataDog/integrations-core/pull/13408))

## 4.1.0 / 2022-11-17

***Added***:

* Added new opLatencies metrics with correct type ([#13336](https://github.com/DataDog/integrations-core/pull/13336))

## 4.0.4 / 2022-10-28 / Agent 7.41.0

***Fixed***:

* Update dependencies ([#13207](https://github.com/DataDog/integrations-core/pull/13207))

## 4.0.3 / 2022-09-29

***Fixed***:

* Fix collection of `fsyncLocked` metric when configured database is not `admin` ([#13020](https://github.com/DataDog/integrations-core/pull/13020))

## 4.0.2 / 2022-09-02 / Agent 7.39.0

***Fixed***:

* Solve issue after migration to pymongo 4 ([#12860](https://github.com/DataDog/integrations-core/pull/12860))
* Refactor Mongo connection process ([#12767](https://github.com/DataDog/integrations-core/pull/12767))

## 4.0.1 / 2022-08-15

***Fixed***:

* Rename SSL parameters ([#12743](https://github.com/DataDog/integrations-core/pull/12743))

## 4.0.0 / 2022-08-05

***Changed***:

* Upgrade pymongo to 4.2 ([#12594](https://github.com/DataDog/integrations-core/pull/12594))

***Added***:

* Support allow invalid hostnames in SSL connections ([#12541](https://github.com/DataDog/integrations-core/pull/12541))
* Added new metrics for oplatencies ([#12479](https://github.com/DataDog/integrations-core/pull/12479))
* Added new metric "mongodb.metrics.queryexecutor.scannedobjectsps" ([#12467](https://github.com/DataDog/integrations-core/pull/12467))
* Add dbnames allowlist config option ([#12450](https://github.com/DataDog/integrations-core/pull/12450))
* Ship `pymongo-srv` to support DNS seed connection schemas ([#12442](https://github.com/DataDog/integrations-core/pull/12442))

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 3.2.3 / 2022-06-27 / Agent 7.38.0

***Fixed***:

* Allow hosts to be a singular value ([#12090](https://github.com/DataDog/integrations-core/pull/12090))

## 3.2.2 / 2022-05-15 / Agent 7.37.0

***Fixed***:

* Capture badly formatted hosts ([#11933](https://github.com/DataDog/integrations-core/pull/11933))

## 3.2.1 / 2022-04-26

***Fixed***:

* Fix passing in username and password as options ([#11525](https://github.com/DataDog/integrations-core/pull/11525))

## 3.2.0 / 2022-04-05 / Agent 7.36.0

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Support newer versions of `click` ([#11746](https://github.com/DataDog/integrations-core/pull/11746))

## 3.1.0 / 2022-02-19 / Agent 7.35.0

***Added***:

* Add `pyproject.toml` file ([#11399](https://github.com/DataDog/integrations-core/pull/11399))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))
* Small code nits ([#11127](https://github.com/DataDog/integrations-core/pull/11127))

## 3.0.0 / 2022-01-08 / Agent 7.34.0

***Changed***:

* Add `server` default group for all monitor special cases ([#10976](https://github.com/DataDog/integrations-core/pull/10976))

***Fixed***:

* Don't add autogenerated comments to deprecation files ([#11014](https://github.com/DataDog/integrations-core/pull/11014))
* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))
* Refresh role on replica sets and add more debug logging ([#10843](https://github.com/DataDog/integrations-core/pull/10843))

## 2.7.1 / 2021-10-25 / Agent 7.33.0

***Fixed***:

* Load CA certs if SSL is enabled and CA certs are not passed in the configurations ([#10377](https://github.com/DataDog/integrations-core/pull/10377))

## 2.7.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))
* Add runtime configuration validation ([#8957](https://github.com/DataDog/integrations-core/pull/8957))

## 2.6.0 / 2021-08-22 / Agent 7.31.0

***Added***:

* Support collection-agnostic aggregations for custom queries ([#9857](https://github.com/DataDog/integrations-core/pull/9857))

## 2.5.0 / 2021-07-12 / Agent 7.30.0

***Added***:

* Bump pymongo to 3.8 ([#9557](https://github.com/DataDog/integrations-core/pull/9557))

***Fixed***:

* Update description of the `hosts` config parameter ([#9542](https://github.com/DataDog/integrations-core/pull/9542))

## 2.4.0 / 2021-04-19 / Agent 7.28.0

***Deprecated***:

* Deprecate connection_scheme ([#9142](https://github.com/DataDog/integrations-core/pull/9142))

***Fixed***:

* Fix authSource config option. ([#9139](https://github.com/DataDog/integrations-core/pull/9139))

## 2.3.1 / 2021-04-06

***Fixed***:

* Fix no_auth support ([#9094](https://github.com/DataDog/integrations-core/pull/9094))

## 2.3.0 / 2021-03-11 / Agent 7.27.0

***Added***:

* Cache API client connection ([#8808](https://github.com/DataDog/integrations-core/pull/8808))

## 2.2.1 / 2021-03-07

***Fixed***:

* Support Alibaba ApsaraDB ([#8316](https://github.com/DataDog/integrations-core/pull/8316))
* Rename config spec example consumer option `default` to `display_default` ([#8593](https://github.com/DataDog/integrations-core/pull/8593))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 2.2.0 / 2021-01-25 / Agent 7.26.0

***Added***:

* Better arbiter support ([#8294](https://github.com/DataDog/integrations-core/pull/8294))

***Fixed***:

* Refactor connection and api ([#8283](https://github.com/DataDog/integrations-core/pull/8283))

## 2.1.1 / 2020-12-11 / Agent 7.25.0

***Fixed***:

* Log custom queries which return an empty result set ([#8105](https://github.com/DataDog/integrations-core/pull/8105))

## 2.1.0 / 2020-11-10 / Agent 7.24.0

***Added***:

* Add mongodb.connection_pool.totalinuse ([#7986](https://github.com/DataDog/integrations-core/pull/7986))

***Fixed***:

* Ignore startup nodes for lagtime ([#7990](https://github.com/DataDog/integrations-core/pull/7990))

## 2.0.3 / 2020-11-09

***Fixed***:

* Fix debug typo for custom queries ([#7969](https://github.com/DataDog/integrations-core/pull/7969))

## 2.0.2 / 2020-11-06

***Fixed***:

* Fix replicaset identification with old configuration ([#7964](https://github.com/DataDog/integrations-core/pull/7964))

## 2.0.1 / 2020-11-06

***Fixed***:

* Add sharding_cluster_role tag to optime_lag metric ([#7956](https://github.com/DataDog/integrations-core/pull/7956))

## 2.0.0 / 2020-10-31

***Changed***:

* Stop collecting custom queries from secondaries by default ([#7794](https://github.com/DataDog/integrations-core/pull/7794))
* Collect only the metrics that make sense based on the type of mongo instance ([#7713](https://github.com/DataDog/integrations-core/pull/7713))

***Added***:

* New replication lag metric collected from the primary ([#7828](https://github.com/DataDog/integrations-core/pull/7828))
* Add the shard cluster role as a tag ([#7834](https://github.com/DataDog/integrations-core/pull/7834))
* Add new metrics for mongos ([#7770](https://github.com/DataDog/integrations-core/pull/7770))
* Allow specifying a different database in custom queries ([#7808](https://github.com/DataDog/integrations-core/pull/7808))
* [doc] Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

***Fixed***:

* Fix warning when adding 'jumbo_chunks' metrics ([#7833](https://github.com/DataDog/integrations-core/pull/7833))
* Fix building of the connection string ([#7744](https://github.com/DataDog/integrations-core/pull/7744))
* Refactor collection logic ([#7615](https://github.com/DataDog/integrations-core/pull/7615))

## 1.16.5 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* Submit collection metrics even if value is zero ([#7606](https://github.com/DataDog/integrations-core/pull/7606))
* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 1.16.4 / 2020-08-19

***Fixed***:

* Avoid depleting collection_metric_names ([#7393](https://github.com/DataDog/integrations-core/pull/7393))

## 1.16.3 / 2020-08-10 / Agent 7.22.0

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))

## 1.16.2 / 2020-06-29 / Agent 7.21.0

***Fixed***:

* Fix template specs typos ([#6912](https://github.com/DataDog/integrations-core/pull/6912))
* Raise an error if only one of `username` or `password` is set ([#6688](https://github.com/DataDog/integrations-core/pull/6688))

## 1.16.1 / 2020-05-19 / Agent 7.20.0

***Fixed***:

* Fix encoding and parsing issues when processing connection configuration ([#6686](https://github.com/DataDog/integrations-core/pull/6686))

## 1.16.0 / 2020-05-17

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.15.0 / 2020-05-05

***Deprecated***:

* Refactor connection configuration ([#6574](https://github.com/DataDog/integrations-core/pull/6574))

## 1.14.0 / 2020-04-04 / Agent 7.19.0

***Added***:

* Add config specs ([#6145](https://github.com/DataDog/integrations-core/pull/6145))

***Fixed***:

* Use new agent signature ([#6085](https://github.com/DataDog/integrations-core/pull/6085))
* Remove logs sourcecategory ([#6121](https://github.com/DataDog/integrations-core/pull/6121))
* Replace deprecated method `database_names` by `list_database_names` ([#5864](https://github.com/DataDog/integrations-core/pull/5864))

## 1.13.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.12.0 / 2019-10-11 / Agent 6.15.0

***Added***:

* Submit version metadata ([#4722](https://github.com/DataDog/integrations-core/pull/4722))

## 1.11.0 / 2019-07-13 / Agent 6.13.0

***Added***:

* Upgrade pymongo to 3.8 ([#4095](https://github.com/DataDog/integrations-core/pull/4095))

## 1.10.3 / 2019-06-18

***Fixed***:

* Reduce doc in configuration file in favor of official documentation ([#3892](https://github.com/DataDog/integrations-core/pull/3892))

## 1.10.2 / 2019-06-06 / Agent 6.12.0

***Fixed***:

* Custom queries: add examples and fix logging ([#3871](https://github.com/DataDog/integrations-core/pull/3871))

## 1.10.1 / 2019-06-05

***Fixed***:

* Add missing metrics ([#3856](https://github.com/DataDog/integrations-core/pull/3856))
* Fix 'custom_queries' field name ([#3868](https://github.com/DataDog/integrations-core/pull/3868))

## 1.10.0 / 2019-06-01

***Added***:

* Add custom query capabilities ([#3796](https://github.com/DataDog/integrations-core/pull/3796))

## 1.9.0 / 2019-05-14

***Added***:

* Add tcmalloc.spinlock_total_delay_ns to mongodb stats ([#3643](https://github.com/DataDog/integrations-core/pull/3643)) Thanks [glenjamin](https://github.com/glenjamin).
* Adhere to code style ([#3540](https://github.com/DataDog/integrations-core/pull/3540))

## 1.8.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Finish Support Python 3 ([#2916](https://github.com/DataDog/integrations-core/pull/2916))
* Support unicode for Python 3 bindings ([#2869](https://github.com/DataDog/integrations-core/pull/2869))

***Fixed***:

* Only run `top` against the admin database ([#2937](https://github.com/DataDog/integrations-core/pull/2937))

## 1.7.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Support Python 3 ([#2623](https://github.com/DataDog/integrations-core/pull/2623))

***Fixed***:

* Use raw string literals when \ is present ([#2465](https://github.com/DataDog/integrations-core/pull/2465))

## 1.6.1 / 2018-09-04 / Agent 6.5.0

***Fixed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.6.0 / 2018-06-13 / Agent 6.4.0

***Changed***:

* [mongo] properly parse metric ([#1498](https://github.com/DataDog/integrations-core/pull/1498))

***Added***:

* [mongo] allow disabling of replica access ([#1516](https://github.com/DataDog/integrations-core/pull/1516))

## 1.5.4

***Added***:

* Allow disabling of replica access. See #1516

## 1.5.3 / 2018-05-11

***Fixed***:

* Added `top` metrics ending in `countps` that properly submit as `rate`s. See #1491

## 1.5.2 / 2018-02-13

***Added***:

* Adding configuration for log collection in `conf.yaml`

***Fixed***:

* Pass replica set metric collection if `replSetGetStatus` command not available ([#1092](https://github)com/DataDog/integrations-core/issues/1092)

## 1.5.1 / 2018-01-10

***Fixed***:

* Pass replica set metric collection if not running standalone instance instead of raising exception ([#915](https://github)com/DataDog/integrations-core/issues/915)

## 1.5.0 / 2017-11-21

***Changed***:

* Filter out oplog entries without a timestamp ([#406](https://github.com/DataDog/integrations-core/issues/406), thanks [@hindmanj](https://github)com/hindmanj)

***Added***:

* Collect metrics about indexes usage ([#823](https://github)com/DataDog/integrations-core/issues/823)
* Upgrading pymongo to version 3.5 ([#747](https://github)com/DataDog/integrations-core/issues/747)

## 1.4.0 / 2017-10-10

***Added***:

* Started monitoring the wiredTiger cache page read/write statistics ([#769](https://github.com/DataDog/integrations-core/issues/769) (Thanks [@dnavre](https://github)com/dnavre))

## 1.3.0 / 2017-08-28

***Changed***:

* Simplify "system.namespaces" usage ([#625](https://github.com/DataDog/integrations-core/issues/625), thanks [@dtbartle](https://github)com/dtbartle)

***Added***:

* Add support for `authSource` parameter in mongo URL ([#691](https://github)com/DataDog/integrations-core/issues/691)

***Fixed***:

* Don't overwrite the higher-level `cli`/`db` for replset stats ([#627](https://github.com/DataDog/integrations-core/issues/627), thanks [@dtbartle](https://github)com/dtbartle)

## 1.2.0 / 2017-07-18

***Added***:

* Add support for `mongo.oplog.*` metrics for Mongo versions  3.x ([#491](https://github)com/DataDog/integrations-core/issues/491)

## 1.1.0 / 2017-06-05

***Changed***:

* Set connectTimeout & serverSelectionTimeout to timeout in config ([#352](https://github)com/DataDog/integrations-core/issues/352)

## 1.0.1 / 2017-04-24

***Fixed***:

* Redact username/password in logs, etc ([#326](https://github.com/DataDog/integrations-core/issues/326) and [#347](https://github)com/DataDog/integrations-core/issues/347)

## 1.0.0 / 2017-03-22

***Added***:

* adds mongo integration.
