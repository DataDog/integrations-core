# CHANGELOG - mongo

<!-- towncrier release notes start -->

## 6.4.0 / 2024-04-26

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
