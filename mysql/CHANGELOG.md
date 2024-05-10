# CHANGELOG - mysql

<!-- towncrier release notes start -->

## 12.4.0 / 2024-04-26

***Added***:

* Update dependencies ([#17319](https://github.com/DataDog/integrations-core/pull/17319))

## 12.3.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Adding a deadlock metric to MySQL databases. ([#16904](https://github.com/DataDog/integrations-core/pull/16904))
* Update custom_queries configuration to support optional collection_interval ([#16957](https://github.com/DataDog/integrations-core/pull/16957))
* Add read_timeout (default to 10s) for reading from the connection in seconds ([#16988](https://github.com/DataDog/integrations-core/pull/16988))
* Tag MySQL integration queries with service:datadog-agent ([#17158](https://github.com/DataDog/integrations-core/pull/17158))

***Fixed***:

* Exclude events_statements_cpu when checking enabled events_statements consumers ([#16924](https://github.com/DataDog/integrations-core/pull/16924))
* Proper handle events_statements_* timer_end overflow ([#16936](https://github.com/DataDog/integrations-core/pull/16936))
* Explicitly activate autocommit mode for monitoring connections ([#17002](https://github.com/DataDog/integrations-core/pull/17002))
* Use digest_text to compute query signature for collected activities ([#17029](https://github.com/DataDog/integrations-core/pull/17029))
* Update the configuration to include the `metric_prefix` option ([#17065](https://github.com/DataDog/integrations-core/pull/17065))

## 12.2.0 / 2024-03-07 / Agent 7.52.0

***Security***:

* Bump cryptography to 42.0.5 ([#17054](https://github.com/DataDog/integrations-core/pull/17054))

## 12.1.0 / 2024-02-16

***Added***:

* DBM integrations now defaulted to use new go-sqllexer pkg to obfuscate sql statements ([#16681](https://github.com/DataDog/integrations-core/pull/16681))

***Fixed***:

* Check performance_schema, userstat and events_wait_current status on every check run. Fixes warning "Query Activity and Wait Event Collection not Enabled" on database restart. ([#16669](https://github.com/DataDog/integrations-core/pull/16669))

## 12.0.0 / 2024-01-05 / Agent 7.51.0

***Changed***:

* Always use the database instance's resolved hostname for metrics regardless of how dbm and disable_generic_tags is set. For non-dbm customers or users of disable_generic_tags, this change will result in the host tag having a different value than before. It is possible that dashboards and monitors using the integration's metrics will need to be updated if they relied on the faulty host tagging. ([#16201](https://github.com/DataDog/integrations-core/pull/16201))
* require python 3 for mysql integration ([#16368](https://github.com/DataDog/integrations-core/pull/16368))

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Update dependencies ([#16394](https://github.com/DataDog/integrations-core/pull/16394)), ([#16448](https://github.com/DataDog/integrations-core/pull/16448))
* add new obfuscator options to customize SQL obfuscation and normaliza… ([#16429](https://github.com/DataDog/integrations-core/pull/16429))

***Fixed***:

* Revert "report sql obfuscation error count (#15990)" ([#16439](https://github.com/DataDog/integrations-core/pull/16439))
* use single quotes in activity query to fix char set issue ([#16454](https://github.com/DataDog/integrations-core/pull/16454))

## 11.4.1 / 2023-12-04 / Agent 7.50.0

***Fixed***:

* Bump the cryptography version to 41.0.6 ([#16322](https://github.com/DataDog/integrations-core/pull/16322))

## 11.4.0 / 2023-11-10

***Added***:

* * Add obfuscation_mode config option to allow enabling obfuscation with go-sqllexer ([#16126](https://github.com/DataDog/integrations-core/pull/16126)) ([#16126](https://github.com/DataDog/integrations-core/pull/16126))
* Updated dependencies. ([#16154](https://github.com/DataDog/integrations-core/pull/16154))

## 11.3.0 / 2023-10-26

***Added***:

* Add support for reporting SQL obfuscation errors ([#15990](https://github.com/DataDog/integrations-core/pull/15990))
* Emit MySQL metrics queries operation time ([#16065](https://github.com/DataDog/integrations-core/pull/16065))

***Fixed***:

* Bump the `pymysql` version to 1.1.0 on Python 3 ([#16042](https://github.com/DataDog/integrations-core/pull/16042))
* Bump the `cryptography` version to 41.0.5 ([#16083](https://github.com/DataDog/integrations-core/pull/16083))

## 11.2.0 / 2023-09-29

***Added***:

* Update Cryptography to 41.0.4 ([#15922](https://github.com/DataDog/integrations-core/pull/15922))
* Add `wsrep_local_{recv,send}_queue` instant metric ([#15841](https://github.com/DataDog/integrations-core/pull/15841)) Thanks [frivoire](https://github.com/frivoire).

## 11.1.0 / 2023-08-18 / Agent 7.48.0

***Added***:

* Add support for sending `database_instance` metadata ([#15524](https://github.com/DataDog/integrations-core/pull/15524))

***Fixed***:

* Bump cryptography to 41.0.3 ([#15517](https://github.com/DataDog/integrations-core/pull/15517))

## 11.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Add support for ingesting mysql config settings ([#15498](https://github.com/DataDog/integrations-core/pull/15498))
* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 10.3.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))
* Make cancel() synchronous in DBMAsyncJob ([#14717](https://github.com/DataDog/integrations-core/pull/14717))

***Fixed***:

* Move cancel waiting logic to test functions for DBMAsyncJob  ([#14773](https://github.com/DataDog/integrations-core/pull/14773))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 10.2.2 / 2023-05-26 / Agent 7.46.0

***Fixed***:

* mysql: don't overwrite table size metrics with sys table size metrics ([#14612](https://github.com/DataDog/integrations-core/pull/14612))
* Rename azure.name configuration key to azure.fully_qualified_domain_name ([#14534](https://github.com/DataDog/integrations-core/pull/14534))
* mysql: fix tracking references to self.check ([#14419](https://github.com/DataDog/integrations-core/pull/14419)) Thanks [asenci](https://github.com/asenci).

## 10.2.1 / 2023-04-21 / Agent 7.45.0

***Fixed***:

* Fix resources not sent on service check metrics ([#14422](https://github.com/DataDog/integrations-core/pull/14422))

## 10.2.0 / 2023-04-14

***Added***:

* Send resource_type/name for mysql integration metrics ([#14333](https://github.com/DataDog/integrations-core/pull/14333))
* Add cloud_metadata to DBM event payloads ([#14312](https://github.com/DataDog/integrations-core/pull/14312))
* Update dependencies ([#14357](https://github.com/DataDog/integrations-core/pull/14357))

***Fixed***:

* Fix MariaDB InnoDB pending flush metric parsing ([#13658](https://github.com/DataDog/integrations-core/pull/13658)) Thanks [Jack97](https://github.com/Jack97).
* Set self._check instance variables to make tracking work ([#14146](https://github.com/DataDog/integrations-core/pull/14146))

## 10.1.0 / 2023-03-03 / Agent 7.44.0

***Added***:

* Add resolved_hostname to metadata ([#14092](https://github.com/DataDog/integrations-core/pull/14092))

## 10.0.0 / 2023-01-20 / Agent 7.43.0

***Changed***:

* Do not create a temporary table for MySQL sampling ([#13561](https://github.com/DataDog/integrations-core/pull/13561))

***Added***:

* Add deprecation notice for `extra_performance_metrics` option ([#13273](https://github.com/DataDog/integrations-core/pull/13273))

***Fixed***:

* Update dependencies ([#13726](https://github.com/DataDog/integrations-core/pull/13726))

## 9.0.1 / 2022-12-09 / Agent 7.42.0

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))
* Update cryptography dependency ([#13367](https://github.com/DataDog/integrations-core/pull/13367))

## 9.0.0 / 2022-10-28 / Agent 7.41.0

***Removed***:

* Remove mysql tag truncation for metrics ([#13212](https://github.com/DataDog/integrations-core/pull/13212))
* Remove socket information from the activity query ([#13196](https://github.com/DataDog/integrations-core/pull/13196))

***Added***:

* Add Agent settings to log original unobfuscated strings ([#12941](https://github.com/DataDog/integrations-core/pull/12941))

***Fixed***:

* Fix non-specific troubleshooting link on explain_plan_procedure_missing configuration error ([#13215](https://github.com/DataDog/integrations-core/pull/13215))
* Fix check failing when missing unnecessary SELECT grant on perf schema ([#13008](https://github.com/DataDog/integrations-core/pull/13008))

## 8.5.1 / 2022-09-16 / Agent 7.40.0

***Fixed***:

* Bumps base check requirement to v25.4.0 ([#12733](https://github.com/DataDog/integrations-core/pull/12733))

## 8.5.0 / 2022-08-05 / Agent 7.39.0

***Added***:

* Add MySQL user connections metric ([#12657](https://github.com/DataDog/integrations-core/pull/12657))

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))
* Pin `pymysql` to `0.10.1` ([#12612](https://github.com/DataDog/integrations-core/pull/12612))

## 8.4.1 / 2022-07-08 / Agent 7.38.0

***Fixed***:

* Fix bug where mysql table row stats were not being collected ([#12472](https://github.com/DataDog/integrations-core/pull/12472))

## 8.4.0 / 2022-06-27

***Added***:

* Add new metric for tables rows stats ([#11043](https://github.com/DataDog/integrations-core/pull/11043)) Thanks [aymeric-ledizes](https://github.com/aymeric-ledizes).

***Fixed***:

* Fix rows with empty SQL text in DBM Activity Query ([#12393](https://github.com/DataDog/integrations-core/pull/12393))
* Stop query activity collection due to misconfiguration ([#12343](https://github.com/DataDog/integrations-core/pull/12343))
* Fix race conditions when running many instances of the Agent ([#12342](https://github.com/DataDog/integrations-core/pull/12342))
* Revert mysql.net.connections metric type ([#12088](https://github.com/DataDog/integrations-core/pull/12088))

## 8.3.2 / 2022-06-08

***Fixed***:

* Fix race conditions when running many instances of the Agent ([#12342](https://github.com/DataDog/integrations-core/pull/12342))

## 8.3.1 / 2022-05-27

***Fixed***:

* Revert mysql.net.connections metric type ([#12088](https://github.com/DataDog/integrations-core/pull/12088))

## 8.3.0 / 2022-05-15

***Added***:

* Add option to keep aliases in mysql (`keep_sql_alias`) ([#12018](https://github.com/DataDog/integrations-core/pull/12018))
* Add support to ingest cloud_metadata for DBM host linking ([#11988](https://github.com/DataDog/integrations-core/pull/11988))
* Add query_truncated field on activity rows ([#11886](https://github.com/DataDog/integrations-core/pull/11886))

***Fixed***:

* Fix uncommented parent options ([#12013](https://github.com/DataDog/integrations-core/pull/12013))

## 8.2.3 / 2022-05-26 / Agent 7.36.1

***Fixed***:

* Revert mysql.net.connections metric type ([#12088](https://github.com/DataDog/integrations-core/pull/12088))

## 8.2.2 / 2022-04-20 / Agent 7.36.0

***Fixed***:

* Fix activity host reporting ([#11854](https://github.com/DataDog/integrations-core/pull/11854))

## 8.2.1 / 2022-04-14

***Fixed***:

* Update base version ([#11825](https://github.com/DataDog/integrations-core/pull/11825))

## 8.2.0 / 2022-04-05

***Added***:

* Add MySQL Active Sessions ([#11709](https://github.com/DataDog/integrations-core/pull/11709))
* Adds check_hostname parameter To MySQL ([#11713](https://github.com/DataDog/integrations-core/pull/11713))
* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))
* Include SQL metadata in FQT ([#11644](https://github.com/DataDog/integrations-core/pull/11644))
* Enable SQL metadata collection by default ([#11604](https://github.com/DataDog/integrations-core/pull/11604))

## 8.1.0 / 2022-02-19 / Agent 7.35.0

***Added***:

* Add `pyproject.toml` file ([#11400](https://github.com/DataDog/integrations-core/pull/11400))
* Add new metric for tables size ([#10674](https://github.com/DataDog/integrations-core/pull/10674)) Thanks [aymeric-ledizes](https://github.com/aymeric-ledizes).
* Report known mysql database configuration errors as warnings ([#11221](https://github.com/DataDog/integrations-core/pull/11221))
* Add prepared_stmt_count metrics to mysql integration ([#11155](https://github.com/DataDog/integrations-core/pull/11155))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))
* Fix only_custom_queries configuration not honored ([#11506](https://github.com/DataDog/integrations-core/pull/11506))
* Remove unused `metric_prefix` in init_config ([#11464](https://github.com/DataDog/integrations-core/pull/11464))
* Update base version ([#11288](https://github.com/DataDog/integrations-core/pull/11288))
* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 8.0.3 / 2022-02-03 / Agent 7.34.0

***Fixed***:

* Update base version ([#11288](https://github.com/DataDog/integrations-core/pull/11288))

## 8.0.2 / 2022-01-21

***Fixed***:

* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 8.0.1 / 2022-01-13

***Fixed***:

* Update base version ([#11117](https://github.com/DataDog/integrations-core/pull/11117))

## 8.0.0 / 2022-01-08

***Changed***:

* Add `server` default group for all monitor special cases ([#10976](https://github.com/DataDog/integrations-core/pull/10976))

***Added***:

* Add statement metadata to events and metrics payload ([#10880](https://github.com/DataDog/integrations-core/pull/10880))
* Add the option to set a reported hostname (MySQL) ([#10687](https://github.com/DataDog/integrations-core/pull/10687))
* Add mysql_version and mysql_flavor to dbm query metrics payloads ([#10915](https://github.com/DataDog/integrations-core/pull/10915))
* Add more galera metrics ([#10675](https://github.com/DataDog/integrations-core/pull/10675)) Thanks [aymeric-ledizes](https://github.com/aymeric-ledizes).
* Add support for group replication ([#10649](https://github.com/DataDog/integrations-core/pull/10649))

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))
* Fix mysql query metric collection not recovering after database restarts ([#10811](https://github.com/DataDog/integrations-core/pull/10811))
* Bump cachetools ([#10742](https://github.com/DataDog/integrations-core/pull/10742))

## 7.0.1 / 2021-11-19 / Agent 7.33.0

***Fixed***:

* Set correct default values and handle redundant values for additional_variable and additional_status ([#10652](https://github.com/DataDog/integrations-core/pull/10652))

## 7.0.0 / 2021-11-13

***Changed***:

* Enable `extra_status_metrics` and `replication` metrics by default when DBM is enabled ([#10541](https://github.com/DataDog/integrations-core/pull/10541))

***Added***:

* Collect additional statuses and variables ([#10573](https://github.com/DataDog/integrations-core/pull/10573)) Thanks [notemusic110](https://github.com/notemusic110).

## 6.1.1 / 2021-10-26 / Agent 7.32.0

***Fixed***:

* Upgrade datadog checks base to 23.1.5 ([#10467](https://github.com/DataDog/integrations-core/pull/10467))

## 6.1.0 / 2021-10-04

***Added***:

* Sync configs with new option and bump base requirement ([#10315](https://github.com/DataDog/integrations-core/pull/10315))
* Update dependencies ([#10228](https://github.com/DataDog/integrations-core/pull/10228))
* disable generic tags in mysql ([#10167](https://github.com/DataDog/integrations-core/pull/10167))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Add server as generic tag ([#10100](https://github.com/DataDog/integrations-core/pull/10100))
* Avoid re-explaining queries that cannot be explained ([#9989](https://github.com/DataDog/integrations-core/pull/9989))

## 6.0.0 / 2021-08-22 / Agent 7.31.0

***Changed***:

* Update mysql obfuscator options config ([#9885](https://github.com/DataDog/integrations-core/pull/9885))
* Send the correct hostname with metrics when DBM is enabled ([#9878](https://github.com/DataDog/integrations-core/pull/9878))

***Added***:

* Add agent version to mysql database monitoring payloads ([#9916](https://github.com/DataDog/integrations-core/pull/9916))
* Add fetching of null row in events_statements_by_digest ([#9892](https://github.com/DataDog/integrations-core/pull/9892))
* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

## 5.0.4 / 2021-07-22 / Agent 7.30.0

***Fixed***:

* Properly allow deprecated required config ([#9750](https://github.com/DataDog/integrations-core/pull/9750))
* Bump `datadog-checks-base` version requirement ([#9718](https://github.com/DataDog/integrations-core/pull/9718))

## 5.0.3 / 2021-07-16

***Fixed***:

* Support old executable names ([#9716](https://github.com/DataDog/integrations-core/pull/9716))

## 5.0.2 / 2021-07-15

***Fixed***:

* fix incorrect `min_collection_interval` on DBM metrics payload ([#9695](https://github.com/DataDog/integrations-core/pull/9695))

## 5.0.1 / 2021-07-13

***Fixed***:

* Fix obfuscator options being converted into bytes rather than string ([#9676](https://github.com/DataDog/integrations-core/pull/9676))

## 5.0.0 / 2021-07-12

***Changed***:

* Change DBM `statement` config keys and metric terminology to `query` ([#9661](https://github.com/DataDog/integrations-core/pull/9661))
* remove execution plan cost extraction ([#9631](https://github.com/DataDog/integrations-core/pull/9631))
* decouple DBM query metrics interval from check run interval ([#9658](https://github.com/DataDog/integrations-core/pull/9658))
* DBM statement_samples enabled by default, rename DBM-enabled key ([#9619](https://github.com/DataDog/integrations-core/pull/9619))

***Added***:

* Add DBM SQL obfuscator options ([#9639](https://github.com/DataDog/integrations-core/pull/9639))
* Add truncated statement indicator to mysql query sample events ([#9620](https://github.com/DataDog/integrations-core/pull/9620))

***Fixed***:

* Bump base package dependency ([#9666](https://github.com/DataDog/integrations-core/pull/9666))

## 4.1.0 / 2021-06-30

***Added***:

* Provide a reason for not having an execution plan (MySQL) ([#9569](https://github.com/DataDog/integrations-core/pull/9569))

***Fixed***:

* Look for mariadbd process for MariaDB 10.5+ ([#9543](https://github.com/DataDog/integrations-core/pull/9543))
* Fix insufficient rate limiting of statement samples  ([#9585](https://github.com/DataDog/integrations-core/pull/9585))

## 4.0.3 / 2021-06-08 / Agent 7.29.0

***Fixed***:

* Enable autocommit on all connections ([#9476](https://github.com/DataDog/integrations-core/pull/9476))

## 4.0.2 / 2021-06-07

***Fixed***:

* Fix missing replication_role tag on DBM metrics & events ([#9486](https://github.com/DataDog/integrations-core/pull/9486))

## 4.0.1 / 2021-06-01

***Fixed***:

* Bump minimum base package requirement ([#9449](https://github.com/DataDog/integrations-core/pull/9449))

## 4.0.0 / 2021-05-28

***Removed***:

* Remove unused query metric limit configuration ([#9376](https://github.com/DataDog/integrations-core/pull/9376))

***Changed***:

* Send database monitoring "full query text" events ([#9397](https://github.com/DataDog/integrations-core/pull/9397))
* Remove `service` event facet ([#9275](https://github.com/DataDog/integrations-core/pull/9275))
* Send database monitoring query metrics to new intake ([#9223](https://github.com/DataDog/integrations-core/pull/9223))

***Added***:

* Adds a `replication_role` tag to metrics emitted from AWS Aurora instances ([#8282](https://github.com/DataDog/integrations-core/pull/8282))

***Fixed***:

* Fix potential erroneous mysql statement metrics on duplicate queries ([#9253](https://github.com/DataDog/integrations-core/pull/9253))

## 3.0.1 / 2021-04-27 / Agent 7.28.0

***Fixed***:

* Account for name change in replica metrics ([#9230](https://github.com/DataDog/integrations-core/pull/9230))

## 3.0.0 / 2021-04-19

***Changed***:

* Submit DBM query samples via new aggregator API ([#9045](https://github.com/DataDog/integrations-core/pull/9045))

***Added***:

* Add runtime configuration validation ([#8958](https://github.com/DataDog/integrations-core/pull/8958))
* Upgrade cryptography to 3.4.6 on Python 3 ([#8764](https://github.com/DataDog/integrations-core/pull/8764))
* Add replication_mode tag to replication service check ([#8753](https://github.com/DataDog/integrations-core/pull/8753))

## 2.3.0 / 2021-03-07 / Agent 7.27.0

***Security***:

* Upgrade cryptography python package ([#8611](https://github.com/DataDog/integrations-core/pull/8611))

***Added***:

* Collect mysql statement samples & execution plans  ([#8629](https://github.com/DataDog/integrations-core/pull/8629))
* Apply default limits to MySQL statement summaries ([#8646](https://github.com/DataDog/integrations-core/pull/8646))

***Fixed***:

* Rename config spec example consumer option `default` to `display_default` ([#8593](https://github.com/DataDog/integrations-core/pull/8593))
* Support newer queries ([#8402](https://github.com/DataDog/integrations-core/pull/8402))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 2.2.1 / 2021-01-29 / Agent 7.26.0

***Fixed***:

* Fix condition for replication status ([#8475](https://github.com/DataDog/integrations-core/pull/8475))

## 2.2.0 / 2021-01-28

***Security***:

* Upgrade cryptography python package ([#8476](https://github.com/DataDog/integrations-core/pull/8476))

## 2.1.3 / 2021-01-25

***Fixed***:

* Simplify replication status check ([#8401](https://github.com/DataDog/integrations-core/pull/8401))
* Refactor replica metrics and add some debug lines ([#8380](https://github.com/DataDog/integrations-core/pull/8380))
* Tighten condition for mysql.replication.slave_running ([#8381](https://github.com/DataDog/integrations-core/pull/8381))

## 2.1.2 / 2020-11-17 / Agent 7.25.0

***Fixed***:

* Add debug log line for replication status ([#8040](https://github.com/DataDog/integrations-core/pull/8040))

## 2.1.1 / 2020-11-10 / Agent 7.24.0

***Fixed***:

* Change `deep_database_monitoring` language from BETA to ALPHA ([#7948](https://github.com/DataDog/integrations-core/pull/7948))
* Fix configuration typo ([#7911](https://github.com/DataDog/integrations-core/pull/7911))

## 2.1.0 / 2020-10-31

***Security***:

* Upgrade `cryptography` dependency ([#7869](https://github.com/DataDog/integrations-core/pull/7869))

***Added***:

* Support MySQL statement-level metrics for deep database monitoring ([#7851](https://github.com/DataDog/integrations-core/pull/7851))
* [doc] Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

***Fixed***:

* Fix config spec default values ([#7687](https://github.com/DataDog/integrations-core/pull/7687))

## 2.0.3 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* Use database config template in existing specs ([#7548](https://github.com/DataDog/integrations-core/pull/7548))
* Do not render null defaults for config spec example consumer ([#7503](https://github.com/DataDog/integrations-core/pull/7503))
* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 2.0.2 / 2020-08-25

***Fixed***:

* Parse byte string versions ([#7425](https://github.com/DataDog/integrations-core/pull/7425))

## 2.0.1 / 2020-08-14 / Agent 7.22.0

***Fixed***:

* Update config spec default values ([#7340](https://github.com/DataDog/integrations-core/pull/7340))

## 2.0.0 / 2020-08-10

***Changed***:

* Fix mysql metric for innodb row lock time ([#7289](https://github.com/DataDog/integrations-core/pull/7289)) Thanks [sayap](https://github.com/sayap).

***Added***:

* Send more useful metrics for wsrep flow control ([#7316](https://github.com/DataDog/integrations-core/pull/7316)) Thanks [sayap](https://github.com/sayap).
* Add ability to specify which charset to use when connecting to mysql ([#7216](https://github.com/DataDog/integrations-core/pull/7216))

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))
* Refactor connection, improve documentation ([#7204](https://github.com/DataDog/integrations-core/pull/7204))
* Extract version utils ([#7198](https://github.com/DataDog/integrations-core/pull/7198))
* Split config out ([#7195](https://github.com/DataDog/integrations-core/pull/7195))

## 1.15.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Catch unicode error ([#6947](https://github.com/DataDog/integrations-core/pull/6947))

***Fixed***:

* Add config spec ([#6908](https://github.com/DataDog/integrations-core/pull/6908))

## 1.14.0 / 2020-06-03

***Added***:

* Add custom queries ([#6776](https://github.com/DataDog/integrations-core/pull/6776))

## 1.13.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 1.12.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Remove logs sourcecategory ([#6121](https://github.com/DataDog/integrations-core/pull/6121))

## 1.12.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.11.0 / 2019-12-20

***Added***:

* Document log_processing_rules for MySQL slow query logs ([#5237](https://github.com/DataDog/integrations-core/pull/5237))

***Fixed***:

* Fix formatting and typos in the MySQL documentation ([#5238](https://github.com/DataDog/integrations-core/pull/5238))
* Improve perf (minor) by only defining metadata namedtuple once ([#5138](https://github.com/DataDog/integrations-core/pull/5138))

## 1.10.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Upgrade cryptography to 2.8 ([#5047](https://github.com/DataDog/integrations-core/pull/5047))
* Submit version metadata ([#4814](https://github.com/DataDog/integrations-core/pull/4814))

***Fixed***:

* Fix TypeError in schema size check ([#5043](https://github.com/DataDog/integrations-core/pull/5043)) Thanks [rayatbuzzfeed](https://github.com/rayatbuzzfeed).

## 1.9.1 / 2019-10-11 / Agent 6.15.0

***Fixed***:

* Fix typo in logs (Instace -> Instance) ([#4715](https://github.com/DataDog/integrations-core/pull/4715)) Thanks [ajacoutot](https://github.com/ajacoutot).

## 1.9.0 / 2019-07-04 / Agent 6.13.0

***Added***:

* Update cryptography version ([#4000](https://github.com/DataDog/integrations-core/pull/4000))

## 1.8.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3541](https://github.com/DataDog/integrations-core/pull/3541))

## 1.7.0 / 2019-02-27 / Agent 6.10.0

***Added***:

* Remove Encrypted column from results ([#3174](https://github.com/DataDog/integrations-core/pull/3174))

## 1.6.0 / 2019-02-18

***Added***:

* Finish Python 3 Support ([#2948](https://github.com/DataDog/integrations-core/pull/2948))

## 1.5.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Support Python 3 ([#2630](https://github.com/DataDog/integrations-core/pull/2630))

***Fixed***:

* Use raw string literals when \ is present ([#2465](https://github.com/DataDog/integrations-core/pull/2465))

## 1.4.0 / 2018-09-04 / Agent 6.5.0

***Added***:

* Add channel tag to replica metrics ([#1753](https://github.com/DataDog/integrations-core/pull/1753))

***Fixed***:

* Make sure all checks' versions are exposed ([#1945](https://github.com/DataDog/integrations-core/pull/1945))
* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.3.0 / 2018-06-13

***Added***:

* Make the max custom queries configurable in the yaml file ([#1713](https://github.com/DataDog/integrations-core/pull/1713))

### 1.2.1 / 2018-05-31

***Fixed***:

* Fix replication data extraction when replication channel is set ([#1639](https://github.com/DataDog/integrations-core/pull/1639))
* Fix error while fetching mysql pid from psutil  ([#1620](https://github.com/DataDog/integrations-core/pull/1620))

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

* Changes default value of `connect_timeout` to 10 ([#1020](https://github)com/DataDog/integrations-core/issues/1020)

## 1.1.0 / 2018-01-10

***Added***:

* Add support for multi-source replication in both MariaDB and MySQL
* tag `mysql.replication.*` metrics with the replication channel name

## 1.0.5 / 2017-11-21

***Fixed***:

* Fixes [#783](https://github.com/DataDog/integrations-core/issues/783)

## 1.0.4 / 2017-08-28

***Fixed***:

* Add new innodb aio read/write format and prevent future crashes from new format ([#660](https://github)com/DataDog/integrations-core/issues/660)
* Fix bug when options dict is empty ([#637](https://github)com/DataDog/integrations-core/issues/637)
* Fix slow query check for 95th us percentile ([#586](https://github.com/DataDog/integrations-core/issues/586), thanks [@EdwardMcConnell](https://github)com/EdwardMcConnell)

## 1.0.3 / 2017-05-11

***Fixed***:

* MySQL: Fix replication service check for <5.6 ([#394](https://github)com/DataDog/integrations-core/issues/394)

## 1.0.2 / 2017-04-24

***Fixed***:

* MySQL: Fix for replication service check ([#329](https://github)com/DataDog/integrations-core/issues/329)

## 1.0.1 / 2017-03-23

***Fixed***:

* MySQL: Allow for configurable collection of replica statuses ([#288](https://github)com/DataDog/integrations-core/issues/288)
* MySQL: Slaves_connected should be a gauge ([#291](https://github)com/DataDog/integrations-core/issues/291)

## 1.0.0 / 2017-03-23

***Added***:

* adds mysql integration.
