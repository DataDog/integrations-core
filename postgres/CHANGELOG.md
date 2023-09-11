# CHANGELOG - postgres

## Unreleased

## 14.2.4 / 2023-09-07

***Fixed***:

* Initialize pg_settings on Postgres check start and lazy load pg_settings if it's not set ([#15773](https://github.com/DataDog/integrations-core/pull/15773))

## 14.2.3 / 2023-09-06

***Fixed***:

* Set lower connection timeout on connection pool to avoid long running checks ([#15768](https://github.com/DataDog/integrations-core/pull/15768))

## 14.2.2 / 2023-09-05

***Fixed***:

* Revise postgresql.replication_delay to Function with Archive WAL-driven PostgreSQL Replica ([#15629](https://github.com/DataDog/integrations-core/pull/15629))
* Pass timeout when connection pool closes ([#15724](https://github.com/DataDog/integrations-core/pull/15724))

## 14.2.1 / 2023-08-29

***Fixed***:

* Return Azure AD auth token in correct format ([#15701](https://github.com/DataDog/integrations-core/pull/15701))

## 14.2.0 / 2023-08-18

***Added***:

* Add schema collection to Postgres integration ([#15484](https://github.com/DataDog/integrations-core/pull/15484))
* Add support for sending `database_instance` metadata ([#15559](https://github.com/DataDog/integrations-core/pull/15559))
* Update dependencies for Agent 7.48 ([#15585](https://github.com/DataDog/integrations-core/pull/15585))
* Add support for authenticating through Azure Managed Identity ([#15609](https://github.com/DataDog/integrations-core/pull/15609))

***Fixed***:

* Fix explaining parameterized queries flood server logs ([#15612](https://github.com/DataDog/integrations-core/pull/15612))
* Update datadog-checks-base dependency version to 32.6.0 ([#15604](https://github.com/DataDog/integrations-core/pull/15604))
* Prevent `command already in progress` errors in the Postgres integration ([#15489](https://github.com/DataDog/integrations-core/pull/15489))

***Fixed***:

* Fix InstanceConfig loading error for `ssl` config ([#15611](https://github.com/DataDog/integrations-core/pull/15611))

## 14.1.0 / 2023-08-10

***Added***:

* Add support to ingest sys.configurations for SQL Server instances ([#15496](https://github.com/DataDog/integrations-core/pull/15496))
* Bump psycopg3 version && add timeouts on blocking functions ([#15492](https://github.com/DataDog/integrations-core/pull/15492))
* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))
* Add `max_connections` config option and enforce it in Postgres integration ([#15194](https://github.com/DataDog/integrations-core/pull/15194))
* Add database autodiscovery to Postgres integration ([#14811](https://github.com/DataDog/integrations-core/pull/14811))

***Fixed***:

* Fix error handling for psycopg3 err messages ([#15488](https://github.com/DataDog/integrations-core/pull/15488))
* Upgrade postgres check to psycopg3 ([#15411](https://github.com/DataDog/integrations-core/pull/15411))
* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 14.0.1 / 2023-07-13 / Agent 7.47.0

***Fixed***:

* Bump the minimum datadog-checks-base version ([#15238](https://github.com/DataDog/integrations-core/pull/15238))

## 14.0.0 / 2023-07-10

***Changed***:

* Require Python 3 for Postgres integration ([#14813](https://github.com/DataDog/integrations-core/pull/14813))

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))
* Add limited pool + LRU cache to MultiDatabaseConnectionPool ([#14786](https://github.com/DataDog/integrations-core/pull/14786))
* Rewrite Postgres size query and add `postgresql.relation.{tuples,pages,all_visible}` + toast_size metrics ([#14500](https://github.com/DataDog/integrations-core/pull/14500))
* Add metrics for timeline id and checkpoint delay ([#14759](https://github.com/DataDog/integrations-core/pull/14759))
* Add `postgresql.wal.*` metrics from `pg_stat_wal`  ([#13768](https://github.com/DataDog/integrations-core/pull/13768))
* PG: Add metrics for wal files: count, size and age ([#13725](https://github.com/DataDog/integrations-core/pull/13725))
*  Allow explain plan collection to be configured separately from activity collection in pg agent ([#14673](https://github.com/DataDog/integrations-core/pull/14673))
* Make cancel() synchronous in DBMAsyncJob ([#14717](https://github.com/DataDog/integrations-core/pull/14717))
* Postgres: Add `postgres.snapshot.{xmin,xmax,xip_count}` metric ([#13777](https://github.com/DataDog/integrations-core/pull/13777))
* Report per-index disk usage metrics for PostgreSQL ([#13880](https://github.com/DataDog/integrations-core/pull/13880)) Thanks [jcoleman](https://github.com/jcoleman).

***Fixed***:

* Fix version parsing of version strings with an edition suffix ([#14803](https://github.com/DataDog/integrations-core/pull/14803))
* Move cancel waiting logic to test functions for DBMAsyncJob  ([#14773](https://github.com/DataDog/integrations-core/pull/14773))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))
* Properly close db connections for metadata check on cancel ([#14709](https://github.com/DataDog/integrations-core/pull/14709))

## 13.7.0 / 2023-05-26 / Agent 7.46.0

***Added***:

* Support IAM-based RDS authentication ([#14581](https://github.com/DataDog/integrations-core/pull/14581))

## 13.6.0 / 2023-05-26

***Deprecated***:

* No longer test postgres 9.5 ([#14582](https://github.com/DataDog/integrations-core/pull/14582))

***Added***:

* Support ingesting pg_settings for `dbm` users ([#14577](https://github.com/DataDog/integrations-core/pull/14577))
* Enable explain parameterized query feature by default ([#14543](https://github.com/DataDog/integrations-core/pull/14543))
* Create `postgresql.uptime` metric ([#14470](https://github.com/DataDog/integrations-core/pull/14470))
* Add pgss dealloc metric ([#14289](https://github.com/DataDog/integrations-core/pull/14289))

***Fixed***:

* Fix pg_replication_slots query generating errors on posgres replica database with replication slot ([#14531](https://github.com/DataDog/integrations-core/pull/14531)) Thanks [boluwaji-deriv](https://github.com/boluwaji-deriv).
* Don't try to collect wal receiver if aurora is detected ([#14537](https://github.com/DataDog/integrations-core/pull/14537))
* Rename azure.name configuration key to azure.fully_qualified_domain_name ([#14532](https://github.com/DataDog/integrations-core/pull/14532))
* Fix query sampler producing constant errors about undefined parameters ([#14440](https://github.com/DataDog/integrations-core/pull/14440))

## 13.5.0 / 2023-04-14 / Agent 7.45.0

***Added***:

* Send resource_type/name for postgres integration metrics ([#14338](https://github.com/DataDog/integrations-core/pull/14338))
* Update dependencies ([#14357](https://github.com/DataDog/integrations-core/pull/14357))
* Add cloud_metadata to DBM event payloads ([#14313](https://github.com/DataDog/integrations-core/pull/14313))
* Add PostgreSQL replication conflict metrics from `pg_stat_database_conflicts` ([#13542](https://github.com/DataDog/integrations-core/pull/13542))
* Add new sessions metrics from PG14 ([#13723](https://github.com/DataDog/integrations-core/pull/13723))

***Fixed***:

* Reduce the number of idle connections opened when running explain plans across databases ([#14164](https://github.com/DataDog/integrations-core/pull/14164))

## 13.4.0 / 2023-03-03 / Agent 7.44.0

***Added***:

* Add resolved_hostname to metadata ([#14092](https://github.com/DataDog/integrations-core/pull/14092))
* Add `postgresql.replication_slot.*` metrics ([#14013](https://github.com/DataDog/integrations-core/pull/14013))
* Add `postgresql.wal_receiver.*` metrics ([#13852](https://github.com/DataDog/integrations-core/pull/13852))

***Fixed***:

* Avoid brief `postgresql.replication_delay` spikes after Postgres restart/reload ([#13796](https://github.com/DataDog/integrations-core/pull/13796))

## 13.3.0 / 2023-01-20 / Agent 7.43.0

***Added***:

* Add `application_name` to activity metrics and report oldest `backend_xmin`, `backend_xid` and `xact_start` ([#13523](https://github.com/DataDog/integrations-core/pull/13523))
* Add SLRU cache metrics for Postgres ([#13476](https://github.com/DataDog/integrations-core/pull/13476))
* Add `postgresql.replication.backend_xmin_age` metric and use `client_addr` as additional label ([#13413](https://github.com/DataDog/integrations-core/pull/13413))

***Fixed***:

* Update dependencies ([#13726](https://github.com/DataDog/integrations-core/pull/13726))
* Fix bug in replication role tag ([#13694](https://github.com/DataDog/integrations-core/pull/13694))
* Bump the base check dependency ([#13643](https://github.com/DataDog/integrations-core/pull/13643))

## 13.2.0 / 2022-12-09 / Agent 7.42.0

***Added***:

* Explain parameterized queries ([#13434](https://github.com/DataDog/integrations-core/pull/13434))
* Add deadlocks monotonic count metric ([#13374](https://github.com/DataDog/integrations-core/pull/13374))

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))
* Fix inflated query metrics when pg_stat_statements.max is set above 10k ([#13426](https://github.com/DataDog/integrations-core/pull/13426))
* Do not install psycopg2-binary on arm macs ([#13343](https://github.com/DataDog/integrations-core/pull/13343))

## 13.1.0 / 2022-10-31 / Agent 7.41.0

***Added***:

* Improve DBM explain plan error collection errors ([#13224](https://github.com/DataDog/integrations-core/pull/13224))

## 13.0.0 / 2022-10-28

***Removed***:

* Remove postgres tag truncation for metrics ([#13210](https://github.com/DataDog/integrations-core/pull/13210))

***Changed***:

* Update default configuration to collect postgres database by default ([#12999](https://github.com/DataDog/integrations-core/pull/12999))

***Added***:

* Add Agent settings to log original unobfuscated strings ([#12926](https://github.com/DataDog/integrations-core/pull/12926))

***Fixed***:

* Fix deprecation warnings with `semver` ([#12967](https://github.com/DataDog/integrations-core/pull/12967))
* Honor `ignore_databases` in query metrics collection ([#12998](https://github.com/DataDog/integrations-core/pull/12998))

## 12.5.1 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))
* Escape underscore in LOCK_METRICS query ([#12652](https://github.com/DataDog/integrations-core/pull/12652))
* Fix operator precedence in relation filter ([#12645](https://github.com/DataDog/integrations-core/pull/12645)) Thanks [jonremy](https://github.com/jonremy).
* Use readonly connections ([#12608](https://github.com/DataDog/integrations-core/pull/12608))
* Add missing arguments to log statement ([#12499](https://github.com/DataDog/integrations-core/pull/12499)) Thanks [carobme](https://github.com/carobme).

## 12.5.0 / 2022-06-27 / Agent 7.38.0

***Added***:

* Track blk_read_time and blk_write_time for Postgres databases if track_io_timing is enabled ([#12380](https://github.com/DataDog/integrations-core/pull/12380))

***Fixed***:

* Fix Postgres calculation of blk_read_time and blk_write_time metrics ([#12399](https://github.com/DataDog/integrations-core/pull/12399))

## 12.4.0 / 2022-05-15 / Agent 7.37.0

***Added***:

* Add option to keep alias and dollar quote functions in postgres (`keep_sql_alias` and `keep_dollar_quoted_func`) ([#12019](https://github.com/DataDog/integrations-core/pull/12019))
* Add support to ingest cloud_metadata for DBM host linking ([#11987](https://github.com/DataDog/integrations-core/pull/11987))
* Add query_truncated field on activity rows ([#11885](https://github.com/DataDog/integrations-core/pull/11885))

***Fixed***:

* Fix uncommented parent options ([#12013](https://github.com/DataDog/integrations-core/pull/12013))

## 12.3.2 / 2022-04-20 / Agent 7.36.0

***Fixed***:

* Fix activity and sample host reporting ([#11855](https://github.com/DataDog/integrations-core/pull/11855))

## 12.3.1 / 2022-04-14

***Fixed***:

* Update base version ([#11824](https://github.com/DataDog/integrations-core/pull/11824))

## 12.3.0 / 2022-04-05

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Fix postgres activity inflated query durations ([#11765](https://github.com/DataDog/integrations-core/pull/11765))

## 12.2.0 / 2022-03-15

***Added***:

* Enable SQL metadata collection by default ([#11602](https://github.com/DataDog/integrations-core/pull/11602))

***Fixed***:

* Include SQL metadata in FQT ([#11640](https://github.com/DataDog/integrations-core/pull/11640))

## 12.1.1 / 2022-03-14 / Agent 7.35.0

***Fixed***:

* Cache pg_stat_activity columns for sampling query ([#11588](https://github.com/DataDog/integrations-core/pull/11588))

## 12.1.0 / 2022-02-19

***Added***:

* Add ability to collect blocking pids for queries run on postgres dbs ([#11497](https://github.com/DataDog/integrations-core/pull/11497))
* Add `pyproject.toml` file ([#11417](https://github.com/DataDog/integrations-core/pull/11417))
* Report known postgres database configuration errors as warnings ([#11209](https://github.com/DataDog/integrations-core/pull/11209))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))
* Update base version ([#11289](https://github.com/DataDog/integrations-core/pull/11289))
* Fix relations config parsing when multiple relations are specified ([#11195](https://github.com/DataDog/integrations-core/pull/11195))
* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 12.0.4 / 2022-02-03 / Agent 7.34.0

***Fixed***:

* Update base version ([#11289](https://github.com/DataDog/integrations-core/pull/11289))

## 12.0.3 / 2022-01-27

***Fixed***:

* Fix relations config parsing when multiple relations are specified ([#11195](https://github.com/DataDog/integrations-core/pull/11195))

## 12.0.2 / 2022-01-21

***Fixed***:

* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 12.0.1 / 2022-01-13

***Fixed***:

* Update base version ([#11116](https://github.com/DataDog/integrations-core/pull/11116))

## 12.0.0 / 2022-01-08

***Changed***:

* Improve internal explain error troubleshooting metrics ([#10933](https://github.com/DataDog/integrations-core/pull/10933))

***Added***:

* Add statement metadata to events and metrics payload ([#10879](https://github.com/DataDog/integrations-core/pull/10879))
* Add the option to set a reported hostname (Postgres) ([#10682](https://github.com/DataDog/integrations-core/pull/10682))
* Add new metric for waiting queries where state is active ([#10734](https://github.com/DataDog/integrations-core/pull/10734)) Thanks [jfrost](https://github.com/jfrost).

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))
* Bump cachetools ([#10742](https://github.com/DataDog/integrations-core/pull/10742))

## 11.1.1 / 2021-11-30 / Agent 7.33.0

***Fixed***:

* Add datname to connections query for postgresql.connections ([#10748](https://github.com/DataDog/integrations-core/pull/10748))

## 11.1.0 / 2021-11-13

***Added***:

* Add internal debug metric for explain error cache length ([#10616](https://github.com/DataDog/integrations-core/pull/10616))
* Add index bloat metric  ([#10431](https://github.com/DataDog/integrations-core/pull/10431))
* Add ssl configuration options to postgres integration ([#10429](https://github.com/DataDog/integrations-core/pull/10429))
* Add postgres vacuumed and autoanalyzed metrics ([#10350](https://github.com/DataDog/integrations-core/pull/10350)) Thanks [jeroenj](https://github.com/jeroenj).
* Add option to disable bloat metrics ([#10406](https://github.com/DataDog/integrations-core/pull/10406))

***Fixed***:

* Use optimized pg_stat_statements function to fetch the count of rows ([#10507](https://github.com/DataDog/integrations-core/pull/10507))

## 11.0.0 / 2021-10-26 / Agent 7.32.0

***Changed***:

* Change `postgresql.connections` metric collection when DBM is enabled  ([#10482](https://github.com/DataDog/integrations-core/pull/10482))

***Fixed***:

* Fix bug in PG activity collection interval logic ([#10487](https://github.com/DataDog/integrations-core/pull/10487))
* Upgrade datadog checks base to 23.1.5 ([#10466](https://github.com/DataDog/integrations-core/pull/10466))

## 10.0.0 / 2021-10-04

***Changed***:

* Add option to disable generic tags ([#10099](https://github.com/DataDog/integrations-core/pull/10099))

***Added***:

* Add support for live queries feature  ([#9866](https://github.com/DataDog/integrations-core/pull/9866))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Bump datadog checks base version ([#10300](https://github.com/DataDog/integrations-core/pull/10300))
* Avoid re-explaining queries that cannot be explained ([#9941](https://github.com/DataDog/integrations-core/pull/9941))

## 9.0.2 / 2021-08-27 / Agent 7.31.0

***Fixed***:

* Fix missing caching of pg_settings ([#10006](https://github.com/DataDog/integrations-core/pull/10006))

## 9.0.1 / 2021-08-25

***Fixed***:

* Fix postgres collection_errors error reference ([#9982](https://github.com/DataDog/integrations-core/pull/9982))

## 9.0.0 / 2021-08-22

***Changed***:

* Update postgres obfuscator options config ([#9884](https://github.com/DataDog/integrations-core/pull/9884))
* Set a default statement timeout for postgres to 5s ([#9847](https://github.com/DataDog/integrations-core/pull/9847))
* Remove messages for integrations for OK service checks ([#9888](https://github.com/DataDog/integrations-core/pull/9888))

***Added***:

* Collect settings from pg_settings and submit pg_stat_statements metrics ([#9928](https://github.com/DataDog/integrations-core/pull/9928))
* Add agent version to postgres database monitoring payloads ([#9917](https://github.com/DataDog/integrations-core/pull/9917))

***Fixed***:

* Send the correct hostname with metrics when DBM is enabled ([#9865](https://github.com/DataDog/integrations-core/pull/9865))
* Revert "Upgrade `psycopg2` on Python 3" ([#9835](https://github.com/DataDog/integrations-core/pull/9835))

## 8.2.0 / 2021-08-03

***Added***:

* Add metric for estimated table bloat percentage ([#9786](https://github.com/DataDog/integrations-core/pull/9786))
* Collect WAL file age metric ([#9784](https://github.com/DataDog/integrations-core/pull/9784))

## 8.1.0 / 2021-07-26

***Added***:

* Add new relation metrics ([#9758](https://github.com/DataDog/integrations-core/pull/9758))
* Use `display_default` as a fallback for `default` when validating config models ([#9739](https://github.com/DataDog/integrations-core/pull/9739))

***Fixed***:

* Fix debug log formatting ([#9752](https://github.com/DataDog/integrations-core/pull/9752))

## 8.0.5 / 2021-07-21 / Agent 7.30.0

***Fixed***:

* Fix wrong errors related to pg_stat_statements setup ([#9733](https://github.com/DataDog/integrations-core/pull/9733))
* Bump `datadog-checks-base` version requirement ([#9719](https://github.com/DataDog/integrations-core/pull/9719))

## 8.0.4 / 2021-07-15

***Fixed***:

* fix incorrect `min_collection_interval` on DBM metrics payload ([#9696](https://github.com/DataDog/integrations-core/pull/9696))

## 8.0.3 / 2021-07-13

***Fixed***:

* fix None-version crash for DBM statement metrics ([#9692](https://github.com/DataDog/integrations-core/pull/9692))

## 8.0.2 / 2021-07-13

***Fixed***:

* Fix obfuscator options being converted into bytes rather than string ([#9677](https://github.com/DataDog/integrations-core/pull/9677))

## 8.0.1 / 2021-07-12

***Fixed***:

* fix broken error handling in reading of pg_settings ([#9672](https://github.com/DataDog/integrations-core/pull/9672))

## 8.0.0 / 2021-07-12

***Changed***:

* Change DBM `statement` config keys and metric terminology to `query` ([#9664](https://github.com/DataDog/integrations-core/pull/9664))
* remove execution plan cost extraction ([#9632](https://github.com/DataDog/integrations-core/pull/9632))
* decouple DBM query metrics interval from check run interval ([#9657](https://github.com/DataDog/integrations-core/pull/9657))
* DBM statement_samples enabled by default, rename DBM-enabled key ([#9618](https://github.com/DataDog/integrations-core/pull/9618))
* Upgrade psycopg2-binary to 2.8.6 ([#9535](https://github.com/DataDog/integrations-core/pull/9535))

***Added***:

* Add DBM SQL obfuscator options ([#9640](https://github.com/DataDog/integrations-core/pull/9640))
* Add truncated statement indicator to postgres query sample events ([#9597](https://github.com/DataDog/integrations-core/pull/9597))
* Add better error handling/reporting for database errors when querying pg_stat_statements ([#9628](https://github.com/DataDog/integrations-core/pull/9628))
* Provide a reason for not having an execution plan (Postgres) ([#9563](https://github.com/DataDog/integrations-core/pull/9563))

***Fixed***:

* Fix insufficient rate limiting of statement samples  ([#9581](https://github.com/DataDog/integrations-core/pull/9581))
* log execution plan collection failure at debug level ([#9562](https://github.com/DataDog/integrations-core/pull/9562))
* Enable autocommit on all connections ([#9494](https://github.com/DataDog/integrations-core/pull/9494))

## 7.0.2 / 2021-06-03 / Agent 7.29.0

***Fixed***:

* Remove instance-level database tag from DBM metrics & events ([#9469](https://github.com/DataDog/integrations-core/pull/9469))

## 7.0.1 / 2021-06-01

***Fixed***:

* Bump minimum base package requirement ([#9449](https://github.com/DataDog/integrations-core/pull/9449))

## 7.0.0 / 2021-05-28

***Removed***:

* Remove unused query metric limit configuration ([#9377](https://github.com/DataDog/integrations-core/pull/9377))

***Changed***:

* Send database monitoring "full query text" events ([#9405](https://github.com/DataDog/integrations-core/pull/9405))
* Exclude `EXPLAIN` queries from `pg_stat_statements` ([#9358](https://github.com/DataDog/integrations-core/pull/9358))
* Extract relations logic to RelationsManager ([#9322](https://github.com/DataDog/integrations-core/pull/9322))
* Collect statement metrics & samples from all databases on host ([#9252](https://github.com/DataDog/integrations-core/pull/9252))
* Remove `service` event facet ([#9275](https://github.com/DataDog/integrations-core/pull/9275))
* Send database monitoring query metrics to new intake ([#9222](https://github.com/DataDog/integrations-core/pull/9222))

***Added***:

* Filter lock relation metrics by relkind ([#9323](https://github.com/DataDog/integrations-core/pull/9323))

***Fixed***:

* Allow strings in relations ([#9432](https://github.com/DataDog/integrations-core/pull/9432))
* Postgres 13 support for statement metrics ([#9365](https://github.com/DataDog/integrations-core/pull/9365))
* Fix erroneous postgres statement metrics on duplicate queries ([#9231](https://github.com/DataDog/integrations-core/pull/9231))

## 6.0.2 / 2021-04-27

***Fixed***:

* Revert way of checking if it's aurora ([#9224](https://github.com/DataDog/integrations-core/pull/9224))

## 6.0.1 / 2021-04-26 / Agent 7.28.0

***Fixed***:

* Fix config validation for `relations` ([#9242](https://github.com/DataDog/integrations-core/pull/9242))

## 6.0.0 / 2021-04-19

***Changed***:

* Submit DBM query samples via new aggregator API ([#9045](https://github.com/DataDog/integrations-core/pull/9045))

***Added***:

* Add runtime configuration validation ([#8971](https://github.com/DataDog/integrations-core/pull/8971))

***Fixed***:

* Fix wrong timestamp for DBM beta feature ([#9024](https://github.com/DataDog/integrations-core/pull/9024))

## 5.4.0 / 2021-03-07 / Agent 7.27.0

***Added***:

* Collect postgres statement samples & execution plans for deep database monitoring ([#8627](https://github.com/DataDog/integrations-core/pull/8627))
* Apply default limits to Postres statement metrics ([#8647](https://github.com/DataDog/integrations-core/pull/8647))

***Fixed***:

* Shutdown statement sampler thread on cancel ([#8766](https://github.com/DataDog/integrations-core/pull/8766))
* Improve orjson compatibility ([#8767](https://github.com/DataDog/integrations-core/pull/8767))

## 5.3.4 / 2021-02-19

***Fixed***:

* Fix query syntax ([#8661](https://github.com/DataDog/integrations-core/pull/8661))

## 5.3.3 / 2021-02-19

***Fixed***:

* Add dbstrict option to limit queries to specified databases ([#8643](https://github.com/DataDog/integrations-core/pull/8643))
* Rename config spec example consumer option `default` to `display_default` ([#8593](https://github.com/DataDog/integrations-core/pull/8593))

## 5.3.2 / 2021-02-01 / Agent 7.26.0

***Fixed***:

* Fix Postgres statements to remove information_schema query ([#8498](https://github.com/DataDog/integrations-core/pull/8498))
* Bump minimum package ([#8443](https://github.com/DataDog/integrations-core/pull/8443))
* Do not run replication metrics on newer aurora versions ([#8492](https://github.com/DataDog/integrations-core/pull/8492))

## 5.3.1 / 2020-12-11 / Agent 7.25.0

***Fixed***:

* Removed duplicated metrics ([#8116](https://github.com/DataDog/integrations-core/pull/8116))

## 5.3.0 / 2020-11-26

***Added***:

* Add new metrics for WAL based logical replication ([#8026](https://github.com/DataDog/integrations-core/pull/8026))

## 5.2.1 / 2020-11-10 / Agent 7.24.0

***Fixed***:

* Fix query tag to use the normalized query ([#7982](https://github.com/DataDog/integrations-core/pull/7982))
* Change `deep_database_monitoring` language from BETA to ALPHA ([#7947](https://github.com/DataDog/integrations-core/pull/7947))

## 5.2.0 / 2020-10-31

***Added***:

* Support postgres statement-level metrics for deep database monitoring ([#7852](https://github.com/DataDog/integrations-core/pull/7852))
* [doc] Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

***Fixed***:

* Fix noisy log when not running on Aurora ([#7542](https://github.com/DataDog/integrations-core/pull/7542)) Thanks [lucasviecelli](https://github.com/lucasviecelli).

## 5.1.0 / 2020-09-09 / Agent 7.23.0

***Added***:

* Allow customizing application name in Postgres database ([#7528](https://github.com/DataDog/integrations-core/pull/7528))

***Fixed***:

* Fix PostgreSQL connection string when using ident authentication ([#7219](https://github.com/DataDog/integrations-core/pull/7219)) Thanks [verdie-g](https://github.com/verdie-g).

## 5.0.3 / 2020-09-02

***Fixed***:

* Cache version and is_aurora independently ([#7480](https://github.com/DataDog/integrations-core/pull/7480))
* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))
* [datadog_checks_dev] Use consistent formatting for boolean values ([#7405](https://github.com/DataDog/integrations-core/pull/7405))

## 5.0.2 / 2020-08-10 / Agent 7.22.0

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))

## 5.0.1 / 2020-07-16

***Fixed***:

* Avoid aurora pg warnings ([#7123](https://github.com/DataDog/integrations-core/pull/7123))

## 5.0.0 / 2020-06-29 / Agent 7.21.0

***Changed***:

* Add `max_relations` config ([#6725](https://github.com/DataDog/integrations-core/pull/6725))

***Added***:

* Add config specs ([#6547](https://github.com/DataDog/integrations-core/pull/6547))

***Fixed***:

* Remove references to `use_psycopg2` ([#6975](https://github.com/DataDog/integrations-core/pull/6975))
* Fix template specs typos ([#6912](https://github.com/DataDog/integrations-core/pull/6912))
* Extract config to new class ([#6500](https://github.com/DataDog/integrations-core/pull/6500))

## 4.0.0 / 2020-05-17 / Agent 7.20.0

***Changed***:

* Postgres lock metrics are relation metrics ([#6498](https://github.com/DataDog/integrations-core/pull/6498))

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))
* Refactor multiple instance to single instance ([#6510](https://github.com/DataDog/integrations-core/pull/6510))

## 3.5.4 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Fix service check on unexpected exception ([#6196](https://github.com/DataDog/integrations-core/pull/6196))
* Remove logs sourcecategory ([#6121](https://github.com/DataDog/integrations-core/pull/6121))

## 3.5.3 / 2020-02-26 / Agent 7.18.0

***Fixed***:

* Rollback db connection when we get a 'FeatureNotSupported' exception ([#5882](https://github.com/DataDog/integrations-core/pull/5882))

## 3.5.2 / 2020-02-22

***Fixed***:

* Handle FeatureNotSupported errors in queries ([#5749](https://github.com/DataDog/integrations-core/pull/5749))

## 3.5.1 / 2020-02-13

***Fixed***:

* Filter out schemas in the queries directly ([#5710](https://github.com/DataDog/integrations-core/pull/5710))
* Refactor query_scope utility method ([#5433](https://github.com/DataDog/integrations-core/pull/5433))

## 3.5.0 / 2019-12-30 / Agent 7.17.0

***Added***:

* Add version metadata ([#4874](https://github.com/DataDog/integrations-core/pull/4874))

***Fixed***:

* Handle connection closed ([#5350](https://github.com/DataDog/integrations-core/pull/5350))

## 3.4.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Add lock_type tag to lock metric ([#5006](https://github.com/DataDog/integrations-core/pull/5006)) Thanks [tjwp](https://github.com/tjwp).
* Extract version utils and use semver for version comparison ([#4844](https://github.com/DataDog/integrations-core/pull/4844))

## 3.3.0 / 2019-10-30

***Added***:

* Upgrade psycopg2-binary to 2.8.4 ([#4840](https://github.com/DataDog/integrations-core/pull/4840))

***Fixed***:

* Remove multi instance from code ([#4831](https://github.com/DataDog/integrations-core/pull/4831))

## 3.2.1 / 2019-10-11 / Agent 6.15.0

***Fixed***:

* Add cache invalidation and better thread lock ([#4723](https://github.com/DataDog/integrations-core/pull/4723))

## 3.2.0 / 2019-09-10

***Added***:

* Add schema tag to Lock and Size metrics ([#3721](https://github.com/DataDog/integrations-core/pull/3721)) Thanks [fischaz](https://github.com/fischaz).

## 3.1.3 / 2019-09-04 / Agent 6.14.0

***Fixed***:

* Catch statement timeouts correctly ([#4501](https://github.com/DataDog/integrations-core/pull/4501))

## 3.1.2 / 2019-08-31

***Fixed***:

* Document new config option ([#4480](https://github.com/DataDog/integrations-core/pull/4480))

## 3.1.1 / 2019-08-30

***Fixed***:

* Fix query condition ([#4484](https://github.com/DataDog/integrations-core/pull/4484)) Thanks [dpierce-aledade](https://github.com/dpierce-aledade).

## 3.1.0 / 2019-08-24

***Added***:

* Make table_count_limit a parameter ([#3729](https://github.com/DataDog/integrations-core/pull/3729)) Thanks [fischaz](https://github.com/fischaz).
* Add postgresql application name to connection ([#4295](https://github.com/DataDog/integrations-core/pull/4295))

## 3.0.0 / 2019-07-12 / Agent 6.13.0

***Changed***:

* Add SSL support for psycopg2, remove pg8000 ([#4096](https://github.com/DataDog/integrations-core/pull/4096))

## 2.9.1 / 2019-07-04

***Fixed***:

* Fix tagging for custom queries using custom tags ([#3930](https://github.com/DataDog/integrations-core/pull/3930))

## 2.9.0 / 2019-06-20

***Added***:

* Add regex matching for per-relation metrics ([#3916](https://github.com/DataDog/integrations-core/pull/3916))

## 2.8.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Upgrade psycopg2-binary to 2.8.2 ([#3649](https://github.com/DataDog/integrations-core/pull/3649))
* Adhere to code style ([#3557](https://github.com/DataDog/integrations-core/pull/3557))

***Fixed***:

* Use configuration user for pgsql activity metric ([#3720](https://github.com/DataDog/integrations-core/pull/3720)) Thanks [fischaz](https://github.com/fischaz).
* Fix schema filtering on query relations ([#3449](https://github.com/DataDog/integrations-core/pull/3449)) Thanks [fischaz](https://github.com/fischaz).

## 2.7.0 / 2019-04-05 / Agent 6.11.0

***Added***:

* Adds an option to tag metrics with `replication_role` ([#2929](https://github.com/DataDog/integrations-core/pull/2929))
* Add `server` tag to metrics and service_check ([#2928](https://github.com/DataDog/integrations-core/pull/2928))

## 2.6.0 / 2019-03-11

***Added***:

* Support multiple rows for custom queries ([#3242](https://github.com/DataDog/integrations-core/pull/3242))

## 2.5.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Finish Python3 Support ([#2949](https://github.com/DataDog/integrations-core/pull/2949))

## 2.4.0 / 2019-01-04 / Agent 6.9.0

***Added***:

* Bump psycopg2-binary version to 2.7.5 ([#2799](https://github.com/DataDog/integrations-core/pull/2799))

## 2.3.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Include db tag with postgresql.locks metrics ([#2567](https://github.com/DataDog/integrations-core/pull/2567)) Thanks [sj26](https://github.com/sj26).
* Support Python 3 ([#2616](https://github.com/DataDog/integrations-core/pull/2616))

## 2.2.3 / 2018-10-14 / Agent 6.6.0

***Fixed***:

* Fix version detection for new development releases ([#2401](https://github.com/DataDog/integrations-core/pull/2401))

## 2.2.2 / 2018-09-11 / Agent 6.5.0

***Fixed***:

* Fix version detection for Postgres v10+ ([#2208](https://github.com/DataDog/integrations-core/pull/2208))

## 2.2.1 / 2018-09-06

***Fixed***:

*  Gracefully handle errors when performing custom_queries ([#2184](https://github.com/DataDog/integrations-core/pull/2184))
* Gracefully handle failed version regex match ([#2178](https://github.com/DataDog/integrations-core/pull/2178))

## 2.2.0 / 2018-09-04

***Added***:

* Add number of "idle in transaction" transactions and open transactions ([#2118](https://github.com/DataDog/integrations-core/pull/2118))
* Implement custom_queries and start deprecating custom_metrics ([#2043](https://github.com/DataDog/integrations-core/pull/2043))
* Re-enable instance tags for server metrics on Agent version 6 ([#2049](https://github.com/DataDog/integrations-core/pull/2049))
* Rename dependency psycopg2 to pyscopg2-binary ([#1842](https://github.com/DataDog/integrations-core/pull/1842))
* Correcting duplicate metric name, add index_rows_fetched ([#1762](https://github.com/DataDog/integrations-core/pull/1762))

***Fixed***:

* Fix Postgres version parsing for beta versions ([#2064](https://github.com/DataDog/integrations-core/pull/2064))
* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 2.1.3 / 2018-06-20 / Agent 6.4.0

***Fixed***:

* Fixed postgres verification script ([#1764](https://github.com/DataDog/integrations-core/pull/1764))

## 2.1.2 / 2018-06-07

***Security***:

* Update psycopg2 for security fixes ([#1538](https://github.com/DataDog/integrations-core/pull/1538))

***Fixed***:

* Fix function metrics tagging issue for no-args functions ([#1452](https://github.com/DataDog/integrations-core/pull/1452)) Thanks [zorgz](https://github.com/zorgz).

## 2.1.1 / 2018-05-11

***Fixed***:

* Adding db rollback when transaction fails in postgres metrics collection. See[#1193](https://github.com/DataDog/integrations-core/pull/1193).

## 2.1.0 / 2018-03-07

***Fixed***:

* Adding support for postgres 10 ([#1172](https://github.com/DataDog/integrations-core/issues/1172))

## 2.0.0 / 2018-02-13

***Deprecated***:

* Starting with agent6 the postgres check no longer tag server wide metrics with instance tags ([#1073](https://github)com/DataDog/integrations-core/issues/1073)

***Added***:

* Adding configuration for log collection in `conf.yaml`

## 1.2.1 / 2018-02-13

***Fixed***:

* Adding instance tags to service check See [#1042](https://github.com/DataDog/integrations-core/issues/1042)

## 1.2.0 / 2017-11-21

***Added***:

* Adding an option to include the default 'postgres' database when gathering stats [#740](https://github.com/DataDog/integrations-core/issues/740)

***Fixed***:

* Allows `schema` as tag for custom metrics when no schema relations have been defined See[#776](https://github.com/DataDog/integrations-core/issues/776)

## 1.1.0 / 2017-08-28

***Changed***:

* Deprecating "postgres.replication_delay_bytes" in favor of "postgresql.replication_delay_bytes". See[#639](https://github.com/DataDog/integrations-core/issues/639) and [#699](https://github.com/DataDog/integrations-core/issues/699), thanks to [@Erouan50](https://github.com/Erouan50)

***Fixed***:

* Allow specifying postgres port as string ([#607](https://github.com/DataDog/integrations-core/issues/607), thanks [@infothrill](https://github)com/infothrill)

## 1.0.3 / 2017-07-18

***Added***:

* Collect pg_stat_archiver stats in PG>=9.4.

## 1.0.2 / 2017-06-05

***Added***:

* Provide a meaningful error when custom metrics are misconfigured ([#446](https://github)com/DataDog/integrations-core/issues/446)

## 1.0.1 / 2017-03-22

***Changed***:

* bump psycopg2 to 2.7.1 ([#295](https://github.com/DataDog/integrations-core/issues/295))

## 1.0.0 / 2017-03-22

***Added***:

* adds postgres integration.
