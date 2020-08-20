# CHANGELOG - mongo

## 1.16.4 / 2020-08-19

* [Fixed] Avoid depleting collection_metric_names. See [#7393](https://github.com/DataDog/integrations-core/pull/7393).

## 1.16.3 / 2020-08-10

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).

## 1.16.2 / 2020-06-29

* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).
* [Fixed] Raise an error if only one of `username` or `password` is set. See [#6688](https://github.com/DataDog/integrations-core/pull/6688).

## 1.16.1 / 2020-05-19

* [Fixed] Fix encoding and parsing issues when processing connection configuration. See [#6686](https://github.com/DataDog/integrations-core/pull/6686).

## 1.16.0 / 2020-05-17

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.15.0 / 2020-05-05

* [Deprecated] Refactor connection configuration. See [#6574](https://github.com/DataDog/integrations-core/pull/6574).

## 1.14.0 / 2020-04-04

* [Added] Add config specs. See [#6145](https://github.com/DataDog/integrations-core/pull/6145).
* [Fixed] Use new agent signature. See [#6085](https://github.com/DataDog/integrations-core/pull/6085).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Fixed] Replace deprecated method `database_names` by `list_database_names`. See [#5864](https://github.com/DataDog/integrations-core/pull/5864).

## 1.13.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.12.0 / 2019-10-11

* [Added] Submit version metadata. See [#4722](https://github.com/DataDog/integrations-core/pull/4722).

## 1.11.0 / 2019-07-13

* [Added] Upgrade pymongo to 3.8. See [#4095](https://github.com/DataDog/integrations-core/pull/4095).

## 1.10.3 / 2019-06-18

* [Fixed] Reduce doc in configuration file in favor of official documentation. See [#3892](https://github.com/DataDog/integrations-core/pull/3892).

## 1.10.2 / 2019-06-06

* [Fixed] Custom queries: add examples and fix logging. See [#3871](https://github.com/DataDog/integrations-core/pull/3871).

## 1.10.1 / 2019-06-05

* [Fixed] Add missing metrics. See [#3856](https://github.com/DataDog/integrations-core/pull/3856).
* [Fixed] Fix 'custom_queries' field name. See [#3868](https://github.com/DataDog/integrations-core/pull/3868).

## 1.10.0 / 2019-06-01

* [Added] Add custom query capabilities. See [#3796](https://github.com/DataDog/integrations-core/pull/3796).

## 1.9.0 / 2019-05-14

* [Added] Add tcmalloc.spinlock_total_delay_ns to mongodb stats. See [#3643](https://github.com/DataDog/integrations-core/pull/3643). Thanks [glenjamin](https://github.com/glenjamin).
* [Added] Adhere to code style. See [#3540](https://github.com/DataDog/integrations-core/pull/3540).

## 1.8.0 / 2019-02-18

* [Added] Finish Support Python 3. See [#2916](https://github.com/DataDog/integrations-core/pull/2916).
* [Fixed] Only run `top` against the admin database. See [#2937](https://github.com/DataDog/integrations-core/pull/2937).
* [Added] Support unicode for Python 3 bindings. See [#2869](https://github.com/DataDog/integrations-core/pull/2869).

## 1.7.0 / 2018-11-30

* [Added] Support Python 3. See [#2623][1].
* [Fixed] Use raw string literals when \ is present. See [#2465][2].

## 1.6.1 / 2018-09-04

* [Fixed] Add data files to the wheel package. See [#1727][3].

## 1.6.0 / 2018-06-13

* [Added] [mongo] allow disabling of replica access. See [#1516][4].
* [Changed] [mongo] properly parse metric. See [#1498][5].

## 1.5.4 / Unreleased

* [IMPROVEMENT] Allow disabling of replica access. See #1516

## 1.5.3 / 2018-05-11

* [BUGFIX] Added `top` metrics ending in `countps` that properly submit as `rate`s. See #1491

## 1.5.2 / 2018-02-13

* [DOC] Adding configuration for log collection in `conf.yaml`
* [BUGFIX] Pass replica set metric collection if `replSetGetStatus` command not available. See [#1092][6]

## 1.5.1 / 2018-01-10

* [BUGFIX] Pass replica set metric collection if not running standalone instance instead of raising exception. See [#915][7]

## 1.5.0 / 2017-11-21

* [FEATURE] Collect metrics about indexes usage. See [#823][8]
* [IMPROVEMENT] Upgrading pymongo to version 3.5. See [#747][9]
* [IMPROVEMENT] Filter out oplog entries without a timestamp. See [#406][10], thanks [@hindmanj][11]

## 1.4.0 / 2017-10-10

* [IMPROVEMENT] Started monitoring the wiredTiger cache page read/write statistics. See [#769][12] (Thanks [@dnavre][13])

## 1.3.0 / 2017-08-28

* [FEATURE] Add support for `authSource` parameter in mongo URL. See [#691][14]
* [IMPROVEMENT] Simplify "system.namespaces" usage. See [#625][15], thanks [@dtbartle][16]
* [BUGFIX] Don't overwrite the higher-level `cli`/`db` for replset stats. See [#627][17], thanks [@dtbartle][16]

## 1.2.0 / 2017-07-18

* [IMPROVEMENT] Add support for `mongo.oplog.*` metrics for Mongo versions  3.x. See [#491][18]

## 1.1.0 / 2017-06-05

* [IMPROVEMENT] Set connectTimeout & serverSelectionTimeout to timeout in config. See [#352][19]

## 1.0.1 / 2017-04-24

* [BUGFIX] Redact username/password in logs, etc. See [#326][20] and [#347][21]

## 1.0.0 / 2017-03-22

* [FEATURE] adds mongo integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2623
[2]: https://github.com/DataDog/integrations-core/pull/2465
[3]: https://github.com/DataDog/integrations-core/pull/1727
[4]: https://github.com/DataDog/integrations-core/pull/1516
[5]: https://github.com/DataDog/integrations-core/pull/1498
[6]: https://github.com/DataDog/integrations-core/issues/1092
[7]: https://github.com/DataDog/integrations-core/issues/915
[8]: https://github.com/DataDog/integrations-core/issues/823
[9]: https://github.com/DataDog/integrations-core/issues/747
[10]: https://github.com/DataDog/integrations-core/issues/406
[11]: https://github.com/hindmanj
[12]: https://github.com/DataDog/integrations-core/issues/769
[13]: https://github.com/dnavre
[14]: https://github.com/DataDog/integrations-core/issues/691
[15]: https://github.com/DataDog/integrations-core/issues/625
[16]: https://github.com/dtbartle
[17]: https://github.com/DataDog/integrations-core/issues/627
[18]: https://github.com/DataDog/integrations-core/issues/491
[19]: https://github.com/DataDog/integrations-core/issues/352
[20]: https://github.com/DataDog/integrations-core/issues/326
[21]: https://github.com/DataDog/integrations-core/issues/347
