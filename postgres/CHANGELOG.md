# CHANGELOG - postgres

## 13.5.0 / 2023-04-14

* [Added] Send resource_type/name for postgres integration metrics. See [#14338](https://github.com/DataDog/integrations-core/pull/14338).
* [Added] Update dependencies. See [#14357](https://github.com/DataDog/integrations-core/pull/14357).
* [Added] Add cloud_metadata to DBM event payloads. See [#14313](https://github.com/DataDog/integrations-core/pull/14313).
* [Added] Add PostgreSQL replication conflict metrics from `pg_stat_database_conflicts`. See [#13542](https://github.com/DataDog/integrations-core/pull/13542).
* [Added] Add new sessions metrics from PG14. See [#13723](https://github.com/DataDog/integrations-core/pull/13723).
* [Fixed] Reduce the number of idle connections opened when running explain plans across databases. See [#14164](https://github.com/DataDog/integrations-core/pull/14164).

## 13.4.0 / 2023-03-03

* [Added] Add resolved_hostname to metadata. See [#14092](https://github.com/DataDog/integrations-core/pull/14092).
* [Added] Add `postgresql.replication_slot.*` metrics. See [#14013](https://github.com/DataDog/integrations-core/pull/14013).
* [Added] Add `postgresql.wal_receiver.*` metrics. See [#13852](https://github.com/DataDog/integrations-core/pull/13852).
* [Fixed] Avoid brief `postgresql.replication_delay` spikes after Postgres restart/reload. See [#13796](https://github.com/DataDog/integrations-core/pull/13796).

## 13.3.0 / 2023-01-20 / Agent 7.43.0

* [Added] Add `application_name` to activity metrics and report oldest `backend_xmin`, `backend_xid` and `xact_start`. See [#13523](https://github.com/DataDog/integrations-core/pull/13523).
* [Added] Add SLRU cache metrics for Postgres. See [#13476](https://github.com/DataDog/integrations-core/pull/13476).
* [Added] Add `postgresql.replication.backend_xmin_age` metric and use `client_addr` as additional label. See [#13413](https://github.com/DataDog/integrations-core/pull/13413).
* [Fixed] Update dependencies. See [#13726](https://github.com/DataDog/integrations-core/pull/13726).
* [Fixed] Fix bug in replication role tag. See [#13694](https://github.com/DataDog/integrations-core/pull/13694).
* [Fixed] Bump the base check dependency. See [#13643](https://github.com/DataDog/integrations-core/pull/13643).

## 13.2.0 / 2022-12-09 / Agent 7.42.0

* [Added] Explain parameterized queries. See [#13434](https://github.com/DataDog/integrations-core/pull/13434).
* [Added] Add deadlocks monotonic count metric. See [#13374](https://github.com/DataDog/integrations-core/pull/13374).
* [Fixed] Update dependencies. See [#13478](https://github.com/DataDog/integrations-core/pull/13478).
* [Fixed] Fix inflated query metrics when pg_stat_statements.max is set above 10k. See [#13426](https://github.com/DataDog/integrations-core/pull/13426).
* [Fixed] Do not install psycopg2-binary on arm macs. See [#13343](https://github.com/DataDog/integrations-core/pull/13343).

## 13.1.0 / 2022-10-31 / Agent 7.41.0

* [Added] Improve DBM explain plan error collection errors. See [#13224](https://github.com/DataDog/integrations-core/pull/13224).

## 13.0.0 / 2022-10-28

* [Added] Add Agent settings to log original unobfuscated strings. See [#12926](https://github.com/DataDog/integrations-core/pull/12926).
* [Fixed] Fix deprecation warnings with `semver`. See [#12967](https://github.com/DataDog/integrations-core/pull/12967).
* [Fixed] Honor `ignore_databases` in query metrics collection. See [#12998](https://github.com/DataDog/integrations-core/pull/12998).
* [Changed] Update default configuration to collect postgres database by default. See [#12999](https://github.com/DataDog/integrations-core/pull/12999).
* [Removed] Remove postgres tag truncation for metrics. See [#13210](https://github.com/DataDog/integrations-core/pull/13210).

## 12.5.1 / 2022-08-05 / Agent 7.39.0

* [Fixed] Dependency updates. See [#12653](https://github.com/DataDog/integrations-core/pull/12653).
* [Fixed] Escape underscore in LOCK_METRICS query. See [#12652](https://github.com/DataDog/integrations-core/pull/12652).
* [Fixed] Fix operator precedence in relation filter. See [#12645](https://github.com/DataDog/integrations-core/pull/12645). Thanks [jonremy](https://github.com/jonremy).
* [Fixed] Use readonly connections. See [#12608](https://github.com/DataDog/integrations-core/pull/12608).
* [Fixed] Add missing arguments to log statement. See [#12499](https://github.com/DataDog/integrations-core/pull/12499). Thanks [carobme](https://github.com/carobme).

## 12.5.0 / 2022-06-27 / Agent 7.38.0

* [Added] Track blk_read_time and blk_write_time for Postgres databases if track_io_timing is enabled. See [#12380](https://github.com/DataDog/integrations-core/pull/12380).
* [Fixed] Fix Postgres calculation of blk_read_time and blk_write_time metrics. See [#12399](https://github.com/DataDog/integrations-core/pull/12399).

## 12.4.0 / 2022-05-15 / Agent 7.37.0

* [Added] Add option to keep alias and dollar quote functions in postgres (`keep_sql_alias` and `keep_dollar_quoted_func`). See [#12019](https://github.com/DataDog/integrations-core/pull/12019).
* [Added] Add support to ingest cloud_metadata for DBM host linking. See [#11987](https://github.com/DataDog/integrations-core/pull/11987).
* [Added] Add query_truncated field on activity rows. See [#11885](https://github.com/DataDog/integrations-core/pull/11885).
* [Fixed] Fix uncommented parent options. See [#12013](https://github.com/DataDog/integrations-core/pull/12013).

## 12.3.2 / 2022-04-20 / Agent 7.36.0

* [Fixed] Fix activity and sample host reporting. See [#11855](https://github.com/DataDog/integrations-core/pull/11855).

## 12.3.1 / 2022-04-14

* [Fixed] Update base version. See [#11824](https://github.com/DataDog/integrations-core/pull/11824).

## 12.3.0 / 2022-04-05

* [Added] Upgrade dependencies. See [#11726](https://github.com/DataDog/integrations-core/pull/11726).
* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* [Fixed] Fix postgres activity inflated query durations. See [#11765](https://github.com/DataDog/integrations-core/pull/11765).

## 12.2.0 / 2022-03-15

* [Added] Enable SQL metadata collection by default. See [#11602](https://github.com/DataDog/integrations-core/pull/11602).
* [Fixed] Include SQL metadata in FQT. See [#11640](https://github.com/DataDog/integrations-core/pull/11640).

## 12.1.1 / 2022-03-14 / Agent 7.35.0

* [Fixed] Cache pg_stat_activity columns for sampling query. See [#11588](https://github.com/DataDog/integrations-core/pull/11588).

## 12.1.0 / 2022-02-19

* [Added] Add ability to collect blocking pids for queries run on postgres dbs. See [#11497](https://github.com/DataDog/integrations-core/pull/11497).
* [Added] Add `pyproject.toml` file. See [#11417](https://github.com/DataDog/integrations-core/pull/11417).
* [Added] Report known postgres database configuration errors as warnings. See [#11209](https://github.com/DataDog/integrations-core/pull/11209).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* [Fixed] Update base version. See [#11289](https://github.com/DataDog/integrations-core/pull/11289).
* [Fixed] Fix relations config parsing when multiple relations are specified. See [#11195](https://github.com/DataDog/integrations-core/pull/11195).
* [Fixed] Fix license header dates in autogenerated files. See [#11187](https://github.com/DataDog/integrations-core/pull/11187).

## 12.0.4 / 2022-02-03 / Agent 7.34.0

* [Fixed] Update base version. See [#11289](https://github.com/DataDog/integrations-core/pull/11289).

## 12.0.3 / 2022-01-27

* [Fixed] Fix relations config parsing when multiple relations are specified. See [#11195](https://github.com/DataDog/integrations-core/pull/11195).

## 12.0.2 / 2022-01-21

* [Fixed] Fix license header dates in autogenerated files. See [#11187](https://github.com/DataDog/integrations-core/pull/11187).

## 12.0.1 / 2022-01-13

* [Fixed] Update base version. See [#11116](https://github.com/DataDog/integrations-core/pull/11116).

## 12.0.0 / 2022-01-08

* [Added] Add statement metadata to events and metrics payload. See [#10879](https://github.com/DataDog/integrations-core/pull/10879).
* [Added] Add the option to set a reported hostname (Postgres). See [#10682](https://github.com/DataDog/integrations-core/pull/10682).
* [Added] Add new metric for waiting queries where state is active. See [#10734](https://github.com/DataDog/integrations-core/pull/10734). Thanks [jfrost](https://github.com/jfrost).
* [Fixed] Add comment to autogenerated model files. See [#10945](https://github.com/DataDog/integrations-core/pull/10945).
* [Fixed] Bump cachetools. See [#10742](https://github.com/DataDog/integrations-core/pull/10742).
* [Changed] Improve internal explain error troubleshooting metrics. See [#10933](https://github.com/DataDog/integrations-core/pull/10933).

## 11.1.1 / 2021-11-30 / Agent 7.33.0

* [Fixed] Add datname to connections query for postgresql.connections. See [#10748](https://github.com/DataDog/integrations-core/pull/10748).

## 11.1.0 / 2021-11-13

* [Added] Add internal debug metric for explain error cache length. See [#10616](https://github.com/DataDog/integrations-core/pull/10616).
* [Added] Add index bloat metric . See [#10431](https://github.com/DataDog/integrations-core/pull/10431).
* [Added] Add ssl configuration options to postgres integration. See [#10429](https://github.com/DataDog/integrations-core/pull/10429).
* [Added] Add postgres vacuumed and autoanalyzed metrics. See [#10350](https://github.com/DataDog/integrations-core/pull/10350). Thanks [jeroenj](https://github.com/jeroenj).
* [Added] Add option to disable bloat metrics. See [#10406](https://github.com/DataDog/integrations-core/pull/10406).
* [Fixed] Use optimized pg_stat_statements function to fetch the count of rows. See [#10507](https://github.com/DataDog/integrations-core/pull/10507).

## 11.0.0 / 2021-10-26 / Agent 7.32.0

* [Fixed] Fix bug in PG activity collection interval logic. See [#10487](https://github.com/DataDog/integrations-core/pull/10487).
* [Fixed] Upgrade datadog checks base to 23.1.5. See [#10466](https://github.com/DataDog/integrations-core/pull/10466).
* [Changed] Change `postgresql.connections` metric collection when DBM is enabled . See [#10482](https://github.com/DataDog/integrations-core/pull/10482).

## 10.0.0 / 2021-10-04

* [Added] Add support for live queries feature . See [#9866](https://github.com/DataDog/integrations-core/pull/9866).
* [Added] Disable generic tags. See [#10027](https://github.com/DataDog/integrations-core/pull/10027).
* [Fixed] Bump datadog checks base version. See [#10300](https://github.com/DataDog/integrations-core/pull/10300).
* [Fixed] Avoid re-explaining queries that cannot be explained. See [#9941](https://github.com/DataDog/integrations-core/pull/9941).
* [Changed] Add option to disable generic tags. See [#10099](https://github.com/DataDog/integrations-core/pull/10099).

## 9.0.2 / 2021-08-27 / Agent 7.31.0

* [Fixed] Fix missing caching of pg_settings. See [#10006](https://github.com/DataDog/integrations-core/pull/10006).

## 9.0.1 / 2021-08-25

* [Fixed] Fix postgres collection_errors error reference. See [#9982](https://github.com/DataDog/integrations-core/pull/9982).

## 9.0.0 / 2021-08-22

* [Added] Collect settings from pg_settings and submit pg_stat_statements metrics. See [#9928](https://github.com/DataDog/integrations-core/pull/9928).
* [Added] Add agent version to postgres database monitoring payloads. See [#9917](https://github.com/DataDog/integrations-core/pull/9917).
* [Fixed] Send the correct hostname with metrics when DBM is enabled. See [#9865](https://github.com/DataDog/integrations-core/pull/9865).
* [Fixed] Revert "Upgrade `psycopg2` on Python 3". See [#9835](https://github.com/DataDog/integrations-core/pull/9835).
* [Changed] Update postgres obfuscator options config. See [#9884](https://github.com/DataDog/integrations-core/pull/9884).
* [Changed] Set a default statement timeout for postgres to 5s. See [#9847](https://github.com/DataDog/integrations-core/pull/9847).
* [Changed] Remove messages for integrations for OK service checks. See [#9888](https://github.com/DataDog/integrations-core/pull/9888).

## 8.2.0 / 2021-08-03

* [Added] Add metric for estimated table bloat percentage. See [#9786](https://github.com/DataDog/integrations-core/pull/9786).
* [Added] Collect WAL file age metric. See [#9784](https://github.com/DataDog/integrations-core/pull/9784).

## 8.1.0 / 2021-07-26

* [Added] Add new relation metrics. See [#9758](https://github.com/DataDog/integrations-core/pull/9758).
* [Added] Use `display_default` as a fallback for `default` when validating config models. See [#9739](https://github.com/DataDog/integrations-core/pull/9739).
* [Fixed] Fix debug log formatting. See [#9752](https://github.com/DataDog/integrations-core/pull/9752).

## 8.0.5 / 2021-07-21 / Agent 7.30.0

* [Fixed] Fix wrong errors related to pg_stat_statements setup. See [#9733](https://github.com/DataDog/integrations-core/pull/9733).
* [Fixed] Bump `datadog-checks-base` version requirement. See [#9719](https://github.com/DataDog/integrations-core/pull/9719).

## 8.0.4 / 2021-07-15

* [Fixed] fix incorrect `min_collection_interval` on DBM metrics payload. See [#9696](https://github.com/DataDog/integrations-core/pull/9696).

## 8.0.3 / 2021-07-13

* [Fixed] fix None-version crash for DBM statement metrics. See [#9692](https://github.com/DataDog/integrations-core/pull/9692).

## 8.0.2 / 2021-07-13

* [Fixed] Fix obfuscator options being converted into bytes rather than string. See [#9677](https://github.com/DataDog/integrations-core/pull/9677).

## 8.0.1 / 2021-07-12

* [Fixed] fix broken error handling in reading of pg_settings. See [#9672](https://github.com/DataDog/integrations-core/pull/9672).

## 8.0.0 / 2021-07-12

* [Added] Add DBM SQL obfuscator options. See [#9640](https://github.com/DataDog/integrations-core/pull/9640).
* [Added] Add truncated statement indicator to postgres query sample events. See [#9597](https://github.com/DataDog/integrations-core/pull/9597).
* [Added] Add better error handling/reporting for database errors when querying pg_stat_statements. See [#9628](https://github.com/DataDog/integrations-core/pull/9628).
* [Added] Provide a reason for not having an execution plan (Postgres). See [#9563](https://github.com/DataDog/integrations-core/pull/9563).
* [Fixed] Fix insufficient rate limiting of statement samples . See [#9581](https://github.com/DataDog/integrations-core/pull/9581).
* [Fixed] log execution plan collection failure at debug level. See [#9562](https://github.com/DataDog/integrations-core/pull/9562).
* [Fixed] Enable autocommit on all connections. See [#9494](https://github.com/DataDog/integrations-core/pull/9494).
* [Changed] Change DBM `statement` config keys and metric terminology to `query`. See [#9664](https://github.com/DataDog/integrations-core/pull/9664).
* [Changed] remove execution plan cost extraction. See [#9632](https://github.com/DataDog/integrations-core/pull/9632).
* [Changed] decouple DBM query metrics interval from check run interval. See [#9657](https://github.com/DataDog/integrations-core/pull/9657).
* [Changed] DBM statement_samples enabled by default, rename DBM-enabled key. See [#9618](https://github.com/DataDog/integrations-core/pull/9618).
* [Changed] Upgrade psycopg2-binary to 2.8.6. See [#9535](https://github.com/DataDog/integrations-core/pull/9535).

## 7.0.2 / 2021-06-03 / Agent 7.29.0

* [Fixed] Remove instance-level database tag from DBM metrics & events. See [#9469](https://github.com/DataDog/integrations-core/pull/9469).

## 7.0.1 / 2021-06-01

* [Fixed] Bump minimum base package requirement. See [#9449](https://github.com/DataDog/integrations-core/pull/9449).

## 7.0.0 / 2021-05-28

* [Added] Filter lock relation metrics by relkind. See [#9323](https://github.com/DataDog/integrations-core/pull/9323).
* [Fixed] Allow strings in relations. See [#9432](https://github.com/DataDog/integrations-core/pull/9432).
* [Fixed] Postgres 13 support for statement metrics. See [#9365](https://github.com/DataDog/integrations-core/pull/9365).
* [Fixed] Fix erroneous postgres statement metrics on duplicate queries. See [#9231](https://github.com/DataDog/integrations-core/pull/9231).
* [Changed] Send database monitoring "full query text" events. See [#9405](https://github.com/DataDog/integrations-core/pull/9405).
* [Changed] Exclude `EXPLAIN` queries from `pg_stat_statements`. See [#9358](https://github.com/DataDog/integrations-core/pull/9358).
* [Changed] Extract relations logic to RelationsManager. See [#9322](https://github.com/DataDog/integrations-core/pull/9322).
* [Changed] Collect statement metrics & samples from all databases on host. See [#9252](https://github.com/DataDog/integrations-core/pull/9252).
* [Changed] Remove `service` event facet. See [#9275](https://github.com/DataDog/integrations-core/pull/9275).
* [Changed] Send database monitoring query metrics to new intake. See [#9222](https://github.com/DataDog/integrations-core/pull/9222).
* [Removed] Remove unused query metric limit configuration. See [#9377](https://github.com/DataDog/integrations-core/pull/9377).

## 6.0.2 / 2021-04-27

* [Fixed] Revert way of checking if it's aurora. See [#9224](https://github.com/DataDog/integrations-core/pull/9224).

## 6.0.1 / 2021-04-26 / Agent 7.28.0

* [Fixed] Fix config validation for `relations`. See [#9242](https://github.com/DataDog/integrations-core/pull/9242).

## 6.0.0 / 2021-04-19

* [Added] Add runtime configuration validation. See [#8971](https://github.com/DataDog/integrations-core/pull/8971).
* [Fixed] Fix wrong timestamp for DBM beta feature. See [#9024](https://github.com/DataDog/integrations-core/pull/9024).
* [Changed] Submit DBM query samples via new aggregator API. See [#9045](https://github.com/DataDog/integrations-core/pull/9045).

## 5.4.0 / 2021-03-07 / Agent 7.27.0

* [Added] Collect postgres statement samples & execution plans for deep database monitoring. See [#8627](https://github.com/DataDog/integrations-core/pull/8627).
* [Added] Apply default limits to Postres statement metrics. See [#8647](https://github.com/DataDog/integrations-core/pull/8647).
* [Fixed] Shutdown statement sampler thread on cancel. See [#8766](https://github.com/DataDog/integrations-core/pull/8766).
* [Fixed] Improve orjson compatibility. See [#8767](https://github.com/DataDog/integrations-core/pull/8767).

## 5.3.4 / 2021-02-19

* [Fixed] Fix query syntax. See [#8661](https://github.com/DataDog/integrations-core/pull/8661).

## 5.3.3 / 2021-02-19

* [Fixed] Add dbstrict option to limit queries to specified databases. See [#8643](https://github.com/DataDog/integrations-core/pull/8643).
* [Fixed] Rename config spec example consumer option `default` to `display_default`. See [#8593](https://github.com/DataDog/integrations-core/pull/8593).

## 5.3.2 / 2021-02-01 / Agent 7.26.0

* [Fixed] Fix Postgres statements to remove information_schema query. See [#8498](https://github.com/DataDog/integrations-core/pull/8498).
* [Fixed] Bump minimum package. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).
* [Fixed] Do not run replication metrics on newer aurora versions. See [#8492](https://github.com/DataDog/integrations-core/pull/8492).

## 5.3.1 / 2020-12-11 / Agent 7.25.0

* [Fixed] Removed duplicated metrics. See [#8116](https://github.com/DataDog/integrations-core/pull/8116).

## 5.3.0 / 2020-11-26

* [Added] Add new metrics for WAL based logical replication. See [#8026](https://github.com/DataDog/integrations-core/pull/8026).

## 5.2.1 / 2020-11-10 / Agent 7.24.0

* [Fixed] Fix query tag to use the normalized query. See [#7982](https://github.com/DataDog/integrations-core/pull/7982).
* [Fixed] Change `deep_database_monitoring` language from BETA to ALPHA. See [#7947](https://github.com/DataDog/integrations-core/pull/7947).

## 5.2.0 / 2020-10-31

* [Added] Support postgres statement-level metrics for deep database monitoring. See [#7852](https://github.com/DataDog/integrations-core/pull/7852).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).
* [Fixed] Fix noisy log when not running on Aurora. See [#7542](https://github.com/DataDog/integrations-core/pull/7542). Thanks [lucasviecelli](https://github.com/lucasviecelli).

## 5.1.0 / 2020-09-09 / Agent 7.23.0

* [Added] Allow customizing application name in Postgres database. See [#7528](https://github.com/DataDog/integrations-core/pull/7528).
* [Fixed] Fix PostgreSQL connection string when using ident authentication. See [#7219](https://github.com/DataDog/integrations-core/pull/7219). Thanks [verdie-g](https://github.com/verdie-g).

## 5.0.3 / 2020-09-02

* [Fixed] Cache version and is_aurora independently. See [#7480](https://github.com/DataDog/integrations-core/pull/7480).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).
* [Fixed] [datadog_checks_dev] Use consistent formatting for boolean values. See [#7405](https://github.com/DataDog/integrations-core/pull/7405).

## 5.0.2 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).

## 5.0.1 / 2020-07-16

* [Fixed] Avoid aurora pg warnings. See [#7123](https://github.com/DataDog/integrations-core/pull/7123).

## 5.0.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add config specs. See [#6547](https://github.com/DataDog/integrations-core/pull/6547).
* [Fixed] Remove references to `use_psycopg2`. See [#6975](https://github.com/DataDog/integrations-core/pull/6975).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).
* [Fixed] Extract config to new class. See [#6500](https://github.com/DataDog/integrations-core/pull/6500).
* [Changed] Add `max_relations` config. See [#6725](https://github.com/DataDog/integrations-core/pull/6725).

## 4.0.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Added] Refactor multiple instance to single instance. See [#6510](https://github.com/DataDog/integrations-core/pull/6510).
* [Changed] Postgres lock metrics are relation metrics. See [#6498](https://github.com/DataDog/integrations-core/pull/6498).

## 3.5.4 / 2020-04-04 / Agent 7.19.0

* [Fixed] Fix service check on unexpected exception. See [#6196](https://github.com/DataDog/integrations-core/pull/6196).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 3.5.3 / 2020-02-26 / Agent 7.18.0

* [Fixed] Rollback db connection when we get a 'FeatureNotSupported' exception. See [#5882](https://github.com/DataDog/integrations-core/pull/5882).

## 3.5.2 / 2020-02-22

* [Fixed] Handle FeatureNotSupported errors in queries. See [#5749](https://github.com/DataDog/integrations-core/pull/5749).

## 3.5.1 / 2020-02-13

* [Fixed] Filter out schemas in the queries directly. See [#5710](https://github.com/DataDog/integrations-core/pull/5710).
* [Fixed] Refactor query_scope utility method. See [#5433](https://github.com/DataDog/integrations-core/pull/5433).

## 3.5.0 / 2019-12-30 / Agent 7.17.0

* [Fixed] Handle connection closed. See [#5350](https://github.com/DataDog/integrations-core/pull/5350).
* [Added] Add version metadata. See [#4874](https://github.com/DataDog/integrations-core/pull/4874).

## 3.4.0 / 2019-12-02 / Agent 7.16.0

* [Added] Add lock_type tag to lock metric. See [#5006](https://github.com/DataDog/integrations-core/pull/5006). Thanks [tjwp](https://github.com/tjwp).
* [Added] Extract version utils and use semver for version comparison. See [#4844](https://github.com/DataDog/integrations-core/pull/4844).

## 3.3.0 / 2019-10-30

* [Fixed] Remove multi instance from code. See [#4831](https://github.com/DataDog/integrations-core/pull/4831).
* [Added] Upgrade psycopg2-binary to 2.8.4. See [#4840](https://github.com/DataDog/integrations-core/pull/4840).

## 3.2.1 / 2019-10-11 / Agent 6.15.0

* [Fixed] Add cache invalidation and better thread lock. See [#4723](https://github.com/DataDog/integrations-core/pull/4723).

## 3.2.0 / 2019-09-10

* [Added] Add schema tag to Lock and Size metrics. See [#3721](https://github.com/DataDog/integrations-core/pull/3721). Thanks [fischaz](https://github.com/fischaz).

## 3.1.3 / 2019-09-04 / Agent 6.14.0

* [Fixed] Catch statement timeouts correctly. See [#4501](https://github.com/DataDog/integrations-core/pull/4501).

## 3.1.2 / 2019-08-31

* [Fixed] Document new config option. See [#4480](https://github.com/DataDog/integrations-core/pull/4480).

## 3.1.1 / 2019-08-30

* [Fixed] Fix query condition. See [#4484](https://github.com/DataDog/integrations-core/pull/4484). Thanks [dpierce-aledade](https://github.com/dpierce-aledade).

## 3.1.0 / 2019-08-24

* [Added] Make table_count_limit a parameter. See [#3729](https://github.com/DataDog/integrations-core/pull/3729). Thanks [fischaz](https://github.com/fischaz).
* [Added] Add postgresql application name to connection. See [#4295](https://github.com/DataDog/integrations-core/pull/4295).

## 3.0.0 / 2019-07-12 / Agent 6.13.0

* [Changed] Add SSL support for psycopg2, remove pg8000. See [#4096](https://github.com/DataDog/integrations-core/pull/4096).

## 2.9.1 / 2019-07-04

* [Fixed] Fix tagging for custom queries using custom tags. See [#3930](https://github.com/DataDog/integrations-core/pull/3930).

## 2.9.0 / 2019-06-20

* [Added] Add regex matching for per-relation metrics. See [#3916](https://github.com/DataDog/integrations-core/pull/3916).

## 2.8.0 / 2019-05-14 / Agent 6.12.0

* [Fixed] Use configuration user for pgsql activity metric. See [#3720](https://github.com/DataDog/integrations-core/pull/3720). Thanks [fischaz](https://github.com/fischaz).
* [Fixed] Fix schema filtering on query relations. See [#3449](https://github.com/DataDog/integrations-core/pull/3449). Thanks [fischaz](https://github.com/fischaz).
* [Added] Upgrade psycopg2-binary to 2.8.2. See [#3649](https://github.com/DataDog/integrations-core/pull/3649).
* [Added] Adhere to code style. See [#3557](https://github.com/DataDog/integrations-core/pull/3557).

## 2.7.0 / 2019-04-05 / Agent 6.11.0

* [Added] Adds an option to tag metrics with `replication_role`. See [#2929](https://github.com/DataDog/integrations-core/pull/2929).
* [Added] Add `server` tag to metrics and service_check. See [#2928](https://github.com/DataDog/integrations-core/pull/2928).

## 2.6.0 / 2019-03-11

* [Added] Support multiple rows for custom queries. See [#3242](https://github.com/DataDog/integrations-core/pull/3242).

## 2.5.0 / 2019-02-18 / Agent 6.10.0

* [Added] Finish Python3 Support. See [#2949](https://github.com/DataDog/integrations-core/pull/2949).

## 2.4.0 / 2019-01-04 / Agent 6.9.0

* [Added] Bump psycopg2-binary version to 2.7.5. See [#2799](https://github.com/DataDog/integrations-core/pull/2799).

## 2.3.0 / 2018-11-30 / Agent 6.8.0

* [Added] Include db tag with postgresql.locks metrics. See [#2567](https://github.com/DataDog/integrations-core/pull/2567). Thanks [sj26](https://github.com/sj26).
* [Added] Support Python 3. See [#2616](https://github.com/DataDog/integrations-core/pull/2616).

## 2.2.3 / 2018-10-14 / Agent 6.6.0

* [Fixed] Fix version detection for new development releases. See [#2401](https://github.com/DataDog/integrations-core/pull/2401).

## 2.2.2 / 2018-09-11 / Agent 6.5.0

* [Fixed] Fix version detection for Postgres v10+. See [#2208](https://github.com/DataDog/integrations-core/pull/2208).

## 2.2.1 / 2018-09-06

* [Fixed]  Gracefully handle errors when performing custom_queries. See [#2184](https://github.com/DataDog/integrations-core/pull/2184).
* [Fixed] Gracefully handle failed version regex match. See [#2178](https://github.com/DataDog/integrations-core/pull/2178).

## 2.2.0 / 2018-09-04

* [Added] Add number of "idle in transaction" transactions and open transactions. See [#2118](https://github.com/DataDog/integrations-core/pull/2118).
* [Added] Implement custom_queries and start deprecating custom_metrics. See [#2043](https://github.com/DataDog/integrations-core/pull/2043).
* [Fixed] Fix Postgres version parsing for beta versions. See [#2064](https://github.com/DataDog/integrations-core/pull/2064).
* [Added] Re-enable instance tags for server metrics on Agent version 6. See [#2049](https://github.com/DataDog/integrations-core/pull/2049).
* [Added] Rename dependency psycopg2 to pyscopg2-binary. See [#1842](https://github.com/DataDog/integrations-core/pull/1842).
* [Added] Correcting duplicate metric name, add index_rows_fetched. See [#1762](https://github.com/DataDog/integrations-core/pull/1762).
* [Fixed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 2.1.3 / 2018-06-20 / Agent 6.4.0

* [Fixed] Fixed postgres verification script. See [#1764](https://github.com/DataDog/integrations-core/pull/1764).

## 2.1.2 / 2018-06-07

* [Fixed] Fix function metrics tagging issue for no-args functions. See [#1452](https://github.com/DataDog/integrations-core/pull/1452). Thanks [zorgz](https://github.com/zorgz).
* [Security] Update psycopg2 for security fixes. See [#1538](https://github.com/DataDog/integrations-core/pull/1538).

## 2.1.1 / 2018-05-11

* [BUGFIX] Adding db rollback when transaction fails in postgres metrics collection. See[#1193](https://github.com/DataDog/integrations-core/pull/1193).

## 2.1.0 / 2018-03-07

* [BUGFIX] Adding support for postgres 10. See [#1172](https://github.com/DataDog/integrations-core/issues/1172).

## 2.0.0 / 2018-02-13

* [DOC] Adding configuration for log collection in `conf.yaml`
* [DEPRECATING] Starting with agent6 the postgres check no longer tag server wide metrics with instance tags. See [#1073](https://github.com/DataDog/integrations-core/issues/1073)

## 1.2.1 / 2018-02-13

* [BUGFIX] Adding instance tags to service check See [#1042](https://github.com/DataDog/integrations-core/issues/1042)

## 1.2.0 / 2017-11-21

* [IMPROVEMENT] Adding an option to include the default 'postgres' database when gathering stats [#740](https://github.com/DataDog/integrations-core/issues/740)
* [BUGFIX] Allows `schema` as tag for custom metrics when no schema relations have been defined See[#776](https://github.com/DataDog/integrations-core/issues/776)

## 1.1.0 / 2017-08-28

* [IMPROVEMENT] Deprecating "postgres.replication_delay_bytes" in favor of "postgresql.replication_delay_bytes". See[#639](https://github.com/DataDog/integrations-core/issues/639) and [#699](https://github.com/DataDog/integrations-core/issues/699), thanks to [@Erouan50](https://github.com/Erouan50)
* [MINOR] Allow specifying postgres port as string. See [#607](https://github.com/DataDog/integrations-core/issues/607), thanks [@infothrill](https://github.com/infothrill)

## 1.0.3 / 2017-07-18

* [FEATURE] Collect pg_stat_archiver stats in PG>=9.4.

## 1.0.2 / 2017-06-05

* [IMPROVEMENT] Provide a meaningful error when custom metrics are misconfigured. See [#446](https://github.com/DataDog/integrations-core/issues/446)

## 1.0.1 / 2017-03-22

* [DEPENDENCY] bump psycopg2 to 2.7.1. See [#295](https://github.com/DataDog/integrations-core/issues/295).

## 1.0.0 / 2017-03-22

* [FEATURE] adds postgres integration.
