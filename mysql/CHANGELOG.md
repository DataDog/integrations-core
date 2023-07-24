# CHANGELOG - mysql

## Unreleased

## 10.3.0 / 2023-07-10

***Added***:

* Bump dependencies for Agent 7.47. See [#15145](https://github.com/DataDog/integrations-core/pull/15145).
* Make cancel() synchronous in DBMAsyncJob. See [#14717](https://github.com/DataDog/integrations-core/pull/14717).

***Fixed***:

* Move cancel waiting logic to test functions for DBMAsyncJob . See [#14773](https://github.com/DataDog/integrations-core/pull/14773).
* Bump Python version from py3.8 to py3.9. See [#14701](https://github.com/DataDog/integrations-core/pull/14701).

## 10.2.2 / 2023-05-26 / Agent 7.46.0

***Fixed***:

* mysql: don't overwrite table size metrics with sys table size metrics. See [#14612](https://github.com/DataDog/integrations-core/pull/14612).
* Rename azure.name configuration key to azure.fully_qualified_domain_name. See [#14534](https://github.com/DataDog/integrations-core/pull/14534).
* mysql: fix tracking references to self.check. See [#14419](https://github.com/DataDog/integrations-core/pull/14419). Thanks [asenci](https://github.com/asenci).

## 10.2.1 / 2023-04-21 / Agent 7.45.0

***Fixed***:

* Fix resources not sent on service check metrics. See [#14422](https://github.com/DataDog/integrations-core/pull/14422).

## 10.2.0 / 2023-04-14

***Added***:

* Send resource_type/name for mysql integration metrics. See [#14333](https://github.com/DataDog/integrations-core/pull/14333).
* Add cloud_metadata to DBM event payloads. See [#14312](https://github.com/DataDog/integrations-core/pull/14312).
* Update dependencies. See [#14357](https://github.com/DataDog/integrations-core/pull/14357).

***Fixed***:

* Fix MariaDB InnoDB pending flush metric parsing. See [#13658](https://github.com/DataDog/integrations-core/pull/13658). Thanks [Jack97](https://github.com/Jack97).
* Set self._check instance variables to make tracking work. See [#14146](https://github.com/DataDog/integrations-core/pull/14146).

## 10.1.0 / 2023-03-03 / Agent 7.44.0

***Added***:

* Add resolved_hostname to metadata. See [#14092](https://github.com/DataDog/integrations-core/pull/14092).

## 10.0.0 / 2023-01-20 / Agent 7.43.0

***Changed***:

* Do not create a temporary table for MySQL sampling. See [#13561](https://github.com/DataDog/integrations-core/pull/13561).

***Added***:

* Add deprecation notice for `extra_performance_metrics` option. See [#13273](https://github.com/DataDog/integrations-core/pull/13273).

***Fixed***:

* Update dependencies. See [#13726](https://github.com/DataDog/integrations-core/pull/13726).

## 9.0.1 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Update dependencies. See [#13478](https://github.com/DataDog/integrations-core/pull/13478).
* Update cryptography dependency. See [#13367](https://github.com/DataDog/integrations-core/pull/13367).

## 9.0.0 / 2022-10-28 / Agent 7.41.0

***Removed***:

* Remove mysql tag truncation for metrics. See [#13212](https://github.com/DataDog/integrations-core/pull/13212).
* Remove socket information from the activity query. See [#13196](https://github.com/DataDog/integrations-core/pull/13196).

***Added***:

* Add Agent settings to log original unobfuscated strings. See [#12941](https://github.com/DataDog/integrations-core/pull/12941).

***Fixed***:

* Fix non-specific troubleshooting link on explain_plan_procedure_missing configuration error. See [#13215](https://github.com/DataDog/integrations-core/pull/13215).
* Fix check failing when missing unnecessary SELECT grant on perf schema. See [#13008](https://github.com/DataDog/integrations-core/pull/13008).

## 8.5.1 / 2022-09-16 / Agent 7.40.0

***Fixed***:

* Bumps base check requirement to v25.4.0. See [#12733](https://github.com/DataDog/integrations-core/pull/12733).

## 8.5.0 / 2022-08-05 / Agent 7.39.0

***Added***:

* Add MySQL user connections metric. See [#12657](https://github.com/DataDog/integrations-core/pull/12657).

***Fixed***:

* Dependency updates. See [#12653](https://github.com/DataDog/integrations-core/pull/12653).
* Pin `pymysql` to `0.10.1`. See [#12612](https://github.com/DataDog/integrations-core/pull/12612).

## 8.4.1 / 2022-07-08 / Agent 7.38.0

***Fixed***:

* Fix bug where mysql table row stats were not being collected. See [#12472](https://github.com/DataDog/integrations-core/pull/12472).

## 8.4.0 / 2022-06-27

***Added***:

* Add new metric for tables rows stats. See [#11043](https://github.com/DataDog/integrations-core/pull/11043). Thanks [aymeric-ledizes](https://github.com/aymeric-ledizes).

***Fixed***:

* Fix rows with empty SQL text in DBM Activity Query. See [#12393](https://github.com/DataDog/integrations-core/pull/12393).
* Stop query activity collection due to misconfiguration. See [#12343](https://github.com/DataDog/integrations-core/pull/12343).
* Fix race conditions when running many instances of the Agent. See [#12342](https://github.com/DataDog/integrations-core/pull/12342).
* Revert mysql.net.connections metric type. See [#12088](https://github.com/DataDog/integrations-core/pull/12088).

## 8.3.2 / 2022-06-08

***Fixed***:

* Fix race conditions when running many instances of the Agent. See [#12342](https://github.com/DataDog/integrations-core/pull/12342).

## 8.3.1 / 2022-05-27

***Fixed***:

* Revert mysql.net.connections metric type. See [#12088](https://github.com/DataDog/integrations-core/pull/12088).

## 8.3.0 / 2022-05-15

***Added***:

* Add option to keep aliases in mysql (`keep_sql_alias`). See [#12018](https://github.com/DataDog/integrations-core/pull/12018).
* Add support to ingest cloud_metadata for DBM host linking. See [#11988](https://github.com/DataDog/integrations-core/pull/11988).
* Add query_truncated field on activity rows. See [#11886](https://github.com/DataDog/integrations-core/pull/11886).

***Fixed***:

* Fix uncommented parent options. See [#12013](https://github.com/DataDog/integrations-core/pull/12013).

## 8.2.3 / 2022-05-26 / Agent 7.36.1

***Fixed***:

* Revert mysql.net.connections metric type. See [#12088](https://github.com/DataDog/integrations-core/pull/12088).

## 8.2.2 / 2022-04-20 / Agent 7.36.0

***Fixed***:

* Fix activity host reporting. See [#11854](https://github.com/DataDog/integrations-core/pull/11854).

## 8.2.1 / 2022-04-14

***Fixed***:

* Update base version. See [#11825](https://github.com/DataDog/integrations-core/pull/11825).

## 8.2.0 / 2022-04-05

***Added***:

* Add MySQL Active Sessions. See [#11709](https://github.com/DataDog/integrations-core/pull/11709).
* Adds check_hostname parameter To MySQL. See [#11713](https://github.com/DataDog/integrations-core/pull/11713).
* Upgrade dependencies. See [#11726](https://github.com/DataDog/integrations-core/pull/11726).
* Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* Include SQL metadata in FQT. See [#11644](https://github.com/DataDog/integrations-core/pull/11644).
* Enable SQL metadata collection by default. See [#11604](https://github.com/DataDog/integrations-core/pull/11604).

## 8.1.0 / 2022-02-19 / Agent 7.35.0

***Added***:

* Add `pyproject.toml` file. See [#11400](https://github.com/DataDog/integrations-core/pull/11400).
* Add new metric for tables size. See [#10674](https://github.com/DataDog/integrations-core/pull/10674). Thanks [aymeric-ledizes](https://github.com/aymeric-ledizes).
* Report known mysql database configuration errors as warnings. See [#11221](https://github.com/DataDog/integrations-core/pull/11221).
* Add prepared_stmt_count metrics to mysql integration. See [#11155](https://github.com/DataDog/integrations-core/pull/11155).

***Fixed***:

* Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* Fix only_custom_queries configuration not honored. See [#11506](https://github.com/DataDog/integrations-core/pull/11506).
* Remove unused `metric_prefix` in init_config. See [#11464](https://github.com/DataDog/integrations-core/pull/11464).
* Update base version. See [#11288](https://github.com/DataDog/integrations-core/pull/11288).
* Fix license header dates in autogenerated files. See [#11187](https://github.com/DataDog/integrations-core/pull/11187).

## 8.0.3 / 2022-02-03 / Agent 7.34.0

***Fixed***:

* Update base version. See [#11288](https://github.com/DataDog/integrations-core/pull/11288).

## 8.0.2 / 2022-01-21

***Fixed***:

* Fix license header dates in autogenerated files. See [#11187](https://github.com/DataDog/integrations-core/pull/11187).

## 8.0.1 / 2022-01-13

***Fixed***:

* Update base version. See [#11117](https://github.com/DataDog/integrations-core/pull/11117).

## 8.0.0 / 2022-01-08

***Changed***:

* Add `server` default group for all monitor special cases. See [#10976](https://github.com/DataDog/integrations-core/pull/10976).

***Added***:

* Add statement metadata to events and metrics payload. See [#10880](https://github.com/DataDog/integrations-core/pull/10880).
* Add the option to set a reported hostname (MySQL). See [#10687](https://github.com/DataDog/integrations-core/pull/10687).
* Add mysql_version and mysql_flavor to dbm query metrics payloads. See [#10915](https://github.com/DataDog/integrations-core/pull/10915).
* Add more galera metrics. See [#10675](https://github.com/DataDog/integrations-core/pull/10675). Thanks [aymeric-ledizes](https://github.com/aymeric-ledizes).
* Add support for group replication. See [#10649](https://github.com/DataDog/integrations-core/pull/10649).

***Fixed***:

* Add comment to autogenerated model files. See [#10945](https://github.com/DataDog/integrations-core/pull/10945).
* Fix mysql query metric collection not recovering after database restarts. See [#10811](https://github.com/DataDog/integrations-core/pull/10811).
* Bump cachetools. See [#10742](https://github.com/DataDog/integrations-core/pull/10742).

## 7.0.1 / 2021-11-19 / Agent 7.33.0

***Fixed***:

* Set correct default values and handle redundant values for additional_variable and additional_status. See [#10652](https://github.com/DataDog/integrations-core/pull/10652).

## 7.0.0 / 2021-11-13

***Changed***:

* Enable `extra_status_metrics` and `replication` metrics by default when DBM is enabled. See [#10541](https://github.com/DataDog/integrations-core/pull/10541).

***Added***:

* Collect additional statuses and variables. See [#10573](https://github.com/DataDog/integrations-core/pull/10573). Thanks [notemusic110](https://github.com/notemusic110).

## 6.1.1 / 2021-10-26 / Agent 7.32.0

***Fixed***:

* Upgrade datadog checks base to 23.1.5. See [#10467](https://github.com/DataDog/integrations-core/pull/10467).

## 6.1.0 / 2021-10-04

***Added***:

* Sync configs with new option and bump base requirement. See [#10315](https://github.com/DataDog/integrations-core/pull/10315).
* Update dependencies. See [#10228](https://github.com/DataDog/integrations-core/pull/10228).
* disable generic tags in mysql. See [#10167](https://github.com/DataDog/integrations-core/pull/10167).
* Disable generic tags. See [#10027](https://github.com/DataDog/integrations-core/pull/10027).

***Fixed***:

* Add server as generic tag. See [#10100](https://github.com/DataDog/integrations-core/pull/10100).
* Avoid re-explaining queries that cannot be explained. See [#9989](https://github.com/DataDog/integrations-core/pull/9989).

## 6.0.0 / 2021-08-22 / Agent 7.31.0

***Changed***:

* Update mysql obfuscator options config. See [#9885](https://github.com/DataDog/integrations-core/pull/9885).
* Send the correct hostname with metrics when DBM is enabled. See [#9878](https://github.com/DataDog/integrations-core/pull/9878).

***Added***:

* Add agent version to mysql database monitoring payloads. See [#9916](https://github.com/DataDog/integrations-core/pull/9916).
* Add fetching of null row in events_statements_by_digest. See [#9892](https://github.com/DataDog/integrations-core/pull/9892).
* Use `display_default` as a fallback for `default` when validating config models. See [#9739](https://github.com/DataDog/integrations-core/pull/9739).

## 5.0.4 / 2021-07-22 / Agent 7.30.0

***Fixed***:

* Properly allow deprecated required config. See [#9750](https://github.com/DataDog/integrations-core/pull/9750).
* Bump `datadog-checks-base` version requirement. See [#9718](https://github.com/DataDog/integrations-core/pull/9718).

## 5.0.3 / 2021-07-16

***Fixed***:

* Support old executable names. See [#9716](https://github.com/DataDog/integrations-core/pull/9716).

## 5.0.2 / 2021-07-15

***Fixed***:

* fix incorrect `min_collection_interval` on DBM metrics payload. See [#9695](https://github.com/DataDog/integrations-core/pull/9695).

## 5.0.1 / 2021-07-13

***Fixed***:

* Fix obfuscator options being converted into bytes rather than string. See [#9676](https://github.com/DataDog/integrations-core/pull/9676).

## 5.0.0 / 2021-07-12

***Changed***:

* Change DBM `statement` config keys and metric terminology to `query`. See [#9661](https://github.com/DataDog/integrations-core/pull/9661).
* remove execution plan cost extraction. See [#9631](https://github.com/DataDog/integrations-core/pull/9631).
* decouple DBM query metrics interval from check run interval. See [#9658](https://github.com/DataDog/integrations-core/pull/9658).
* DBM statement_samples enabled by default, rename DBM-enabled key. See [#9619](https://github.com/DataDog/integrations-core/pull/9619).

***Added***:

* Add DBM SQL obfuscator options. See [#9639](https://github.com/DataDog/integrations-core/pull/9639).
* Add truncated statement indicator to mysql query sample events. See [#9620](https://github.com/DataDog/integrations-core/pull/9620).

***Fixed***:

* Bump base package dependency. See [#9666](https://github.com/DataDog/integrations-core/pull/9666).

## 4.1.0 / 2021-06-30

***Added***:

* Provide a reason for not having an execution plan (MySQL). See [#9569](https://github.com/DataDog/integrations-core/pull/9569).

***Fixed***:

* Look for mariadbd process for MariaDB 10.5+. See [#9543](https://github.com/DataDog/integrations-core/pull/9543).
* Fix insufficient rate limiting of statement samples . See [#9585](https://github.com/DataDog/integrations-core/pull/9585).

## 4.0.3 / 2021-06-08 / Agent 7.29.0

***Fixed***:

* Enable autocommit on all connections. See [#9476](https://github.com/DataDog/integrations-core/pull/9476).

## 4.0.2 / 2021-06-07

***Fixed***:

* Fix missing replication_role tag on DBM metrics & events. See [#9486](https://github.com/DataDog/integrations-core/pull/9486).

## 4.0.1 / 2021-06-01

***Fixed***:

* Bump minimum base package requirement. See [#9449](https://github.com/DataDog/integrations-core/pull/9449).

## 4.0.0 / 2021-05-28

***Removed***:

* Remove unused query metric limit configuration. See [#9376](https://github.com/DataDog/integrations-core/pull/9376).

***Changed***:

* Send database monitoring "full query text" events. See [#9397](https://github.com/DataDog/integrations-core/pull/9397).
* Remove `service` event facet. See [#9275](https://github.com/DataDog/integrations-core/pull/9275).
* Send database monitoring query metrics to new intake. See [#9223](https://github.com/DataDog/integrations-core/pull/9223).

***Added***:

* Adds a `replication_role` tag to metrics emitted from AWS Aurora instances. See [#8282](https://github.com/DataDog/integrations-core/pull/8282).

***Fixed***:

* Fix potential erroneous mysql statement metrics on duplicate queries. See [#9253](https://github.com/DataDog/integrations-core/pull/9253).

## 3.0.1 / 2021-04-27 / Agent 7.28.0

***Fixed***:

* Account for name change in replica metrics. See [#9230](https://github.com/DataDog/integrations-core/pull/9230).

## 3.0.0 / 2021-04-19

***Changed***:

* Submit DBM query samples via new aggregator API. See [#9045](https://github.com/DataDog/integrations-core/pull/9045).

***Added***:

* Add runtime configuration validation. See [#8958](https://github.com/DataDog/integrations-core/pull/8958).
* Upgrade cryptography to 3.4.6 on Python 3. See [#8764](https://github.com/DataDog/integrations-core/pull/8764).
* Add replication_mode tag to replication service check. See [#8753](https://github.com/DataDog/integrations-core/pull/8753).

## 2.3.0 / 2021-03-07 / Agent 7.27.0

***Security***:

* Upgrade cryptography python package. See [#8611](https://github.com/DataDog/integrations-core/pull/8611).

***Added***:

* Collect mysql statement samples & execution plans . See [#8629](https://github.com/DataDog/integrations-core/pull/8629).
* Apply default limits to MySQL statement summaries. See [#8646](https://github.com/DataDog/integrations-core/pull/8646).

***Fixed***:

* Rename config spec example consumer option `default` to `display_default`. See [#8593](https://github.com/DataDog/integrations-core/pull/8593).
* Support newer queries. See [#8402](https://github.com/DataDog/integrations-core/pull/8402).
* Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 2.2.1 / 2021-01-29 / Agent 7.26.0

***Fixed***:

* Fix condition for replication status. See [#8475](https://github.com/DataDog/integrations-core/pull/8475).

## 2.2.0 / 2021-01-28

***Security***:

* Upgrade cryptography python package. See [#8476](https://github.com/DataDog/integrations-core/pull/8476).

## 2.1.3 / 2021-01-25

***Fixed***:

* Simplify replication status check. See [#8401](https://github.com/DataDog/integrations-core/pull/8401).
* Refactor replica metrics and add some debug lines. See [#8380](https://github.com/DataDog/integrations-core/pull/8380).
* Tighten condition for mysql.replication.slave_running. See [#8381](https://github.com/DataDog/integrations-core/pull/8381).

## 2.1.2 / 2020-11-17 / Agent 7.25.0

***Fixed***:

* Add debug log line for replication status. See [#8040](https://github.com/DataDog/integrations-core/pull/8040).

## 2.1.1 / 2020-11-10 / Agent 7.24.0

***Fixed***:

* Change `deep_database_monitoring` language from BETA to ALPHA. See [#7948](https://github.com/DataDog/integrations-core/pull/7948).
* Fix configuration typo. See [#7911](https://github.com/DataDog/integrations-core/pull/7911).

## 2.1.0 / 2020-10-31

***Security***:

* Upgrade `cryptography` dependency. See [#7869](https://github.com/DataDog/integrations-core/pull/7869).

***Added***:

* Support MySQL statement-level metrics for deep database monitoring. See [#7851](https://github.com/DataDog/integrations-core/pull/7851).
* [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

***Fixed***:

* Fix config spec default values. See [#7687](https://github.com/DataDog/integrations-core/pull/7687).

## 2.0.3 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* Use database config template in existing specs. See [#7548](https://github.com/DataDog/integrations-core/pull/7548).
* Do not render null defaults for config spec example consumer. See [#7503](https://github.com/DataDog/integrations-core/pull/7503).
* Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 2.0.2 / 2020-08-25

***Fixed***:

* Parse byte string versions. See [#7425](https://github.com/DataDog/integrations-core/pull/7425).

## 2.0.1 / 2020-08-14 / Agent 7.22.0

***Fixed***:

* Update config spec default values. See [#7340](https://github.com/DataDog/integrations-core/pull/7340).

## 2.0.0 / 2020-08-10

***Changed***:

* Fix mysql metric for innodb row lock time. See [#7289](https://github.com/DataDog/integrations-core/pull/7289). Thanks [sayap](https://github.com/sayap).

***Added***:

* Send more useful metrics for wsrep flow control. See [#7316](https://github.com/DataDog/integrations-core/pull/7316). Thanks [sayap](https://github.com/sayap).
* Add ability to specify which charset to use when connecting to mysql. See [#7216](https://github.com/DataDog/integrations-core/pull/7216).

***Fixed***:

* Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).
* Refactor connection, improve documentation. See [#7204](https://github.com/DataDog/integrations-core/pull/7204).
* Extract version utils. See [#7198](https://github.com/DataDog/integrations-core/pull/7198).
* Split config out. See [#7195](https://github.com/DataDog/integrations-core/pull/7195).

## 1.15.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Catch unicode error. See [#6947](https://github.com/DataDog/integrations-core/pull/6947).

***Fixed***:

* Add config spec. See [#6908](https://github.com/DataDog/integrations-core/pull/6908).

## 1.14.0 / 2020-06-03

***Added***:

* Add custom queries. See [#6776](https://github.com/DataDog/integrations-core/pull/6776).

## 1.13.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 1.12.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 1.12.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.11.0 / 2019-12-20

***Added***:

* Document log_processing_rules for MySQL slow query logs. See [#5237](https://github.com/DataDog/integrations-core/pull/5237).

***Fixed***:

* Fix formatting and typos in the MySQL documentation. See [#5238](https://github.com/DataDog/integrations-core/pull/5238).
* Improve perf (minor) by only defining metadata namedtuple once. See [#5138](https://github.com/DataDog/integrations-core/pull/5138).

## 1.10.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Upgrade cryptography to 2.8. See [#5047](https://github.com/DataDog/integrations-core/pull/5047).
* Submit version metadata. See [#4814](https://github.com/DataDog/integrations-core/pull/4814).

***Fixed***:

* Fix TypeError in schema size check. See [#5043](https://github.com/DataDog/integrations-core/pull/5043). Thanks [rayatbuzzfeed](https://github.com/rayatbuzzfeed).

## 1.9.1 / 2019-10-11 / Agent 6.15.0

***Fixed***:

* Fix typo in logs (Instace -> Instance). See [#4715](https://github.com/DataDog/integrations-core/pull/4715). Thanks [ajacoutot](https://github.com/ajacoutot).

## 1.9.0 / 2019-07-04 / Agent 6.13.0

***Added***:

* Update cryptography version. See [#4000](https://github.com/DataDog/integrations-core/pull/4000).

## 1.8.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style. See [#3541](https://github.com/DataDog/integrations-core/pull/3541).

## 1.7.0 / 2019-02-27 / Agent 6.10.0

***Added***:

* Remove Encrypted column from results. See [#3174](https://github.com/DataDog/integrations-core/pull/3174).

## 1.6.0 / 2019-02-18

***Added***:

* Finish Python 3 Support. See [#2948](https://github.com/DataDog/integrations-core/pull/2948).

## 1.5.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Support Python 3. See [#2630](https://github.com/DataDog/integrations-core/pull/2630).

***Fixed***:

* Use raw string literals when \ is present. See [#2465](https://github.com/DataDog/integrations-core/pull/2465).

## 1.4.0 / 2018-09-04 / Agent 6.5.0

***Added***:

* Add channel tag to replica metrics. See [#1753](https://github.com/DataDog/integrations-core/pull/1753).

***Fixed***:

* Make sure all checks' versions are exposed. See [#1945](https://github.com/DataDog/integrations-core/pull/1945).
* Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 1.3.0 / 2018-06-13

***Added***:

* Make the max custom queries configurable in the yaml file. See [#1713](https://github.com/DataDog/integrations-core/pull/1713).

### 1.2.1 / 2018-05-31

***Fixed***:

* Fix replication data extraction when replication channel is set. See [#1639](https://github.com/DataDog/integrations-core/pull/1639).
* Fix error while fetching mysql pid from psutil . See [#1620](https://github.com/DataDog/integrations-core/pull/1620).

## 1.2.0 / 2018-05-11

***Added***:

* Add custom tag support to service checks.

***Fixed***:

* reports slave_service check as `CRITICAL` if `Slave_running` global variable is OFF.

## 1.1.3 / 2018-03-23

***Changed***:

* Bump the pymysql version from 0.6.6 to 0.8.0

***Fixed***:

* Fixes the buffer pool metric to return the aggregated values

## 1.1.2 / 2018-02-13

***Added***:

* Adding configuration for log collection in `conf.yaml`

## 1.1.1 / 2018-02-13

***Fixed***:

* Changes default value of `connect_timeout` to 10. See [#1020](https://github.com/DataDog/integrations-core/issues/1020)

## 1.1.0 / 2018-01-10

***Added***:

* Add support for multi-source replication in both MariaDB and MySQL
* tag `mysql.replication.*` metrics with the replication channel name

## 1.0.5 / 2017-11-21

***Fixed***:

* Fixes [#783](https://github.com/DataDog/integrations-core/issues/783)

## 1.0.4 / 2017-08-28

***Fixed***:

* Add new innodb aio read/write format and prevent future crashes from new format. See [#660](https://github.com/DataDog/integrations-core/issues/660)
* Fix bug when options dict is empty. See [#637](https://github.com/DataDog/integrations-core/issues/637)
* Fix slow query check for 95th us percentile. See [#586](https://github.com/DataDog/integrations-core/issues/586), thanks [@EdwardMcConnell](https://github.com/EdwardMcConnell)

## 1.0.3 / 2017-05-11

***Fixed***:

* MySQL: Fix replication service check for <5.6. See [#394](https://github.com/DataDog/integrations-core/issues/394)

## 1.0.2 / 2017-04-24

***Fixed***:

* MySQL: Fix for replication service check. See [#329](https://github.com/DataDog/integrations-core/issues/329)

## 1.0.1 / 2017-03-23

***Fixed***:

* MySQL: Allow for configurable collection of replica statuses. See [#288](https://github.com/DataDog/integrations-core/issues/288)
* MySQL: Slaves_connected should be a gauge. See [#291](https://github.com/DataDog/integrations-core/issues/291)

## 1.0.0 / 2017-03-23

***Added***:

* adds mysql integration.
