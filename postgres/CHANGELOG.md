# CHANGELOG - postgres

## 3.5.4 / 2020-04-04

* [Fixed] Fix service check on unexpected exception. See [#6196](https://github.com/DataDog/integrations-core/pull/6196).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 3.5.3 / 2020-02-26

* [Fixed] Rollback db connection when we get a 'FeatureNotSupported' exception. See [#5882](https://github.com/DataDog/integrations-core/pull/5882).

## 3.5.2 / 2020-02-22

* [Fixed] Handle FeatureNotSupported errors in queries. See [#5749](https://github.com/DataDog/integrations-core/pull/5749).

## 3.5.1 / 2020-02-13

* [Fixed] Filter out schemas in the queries directly. See [#5710](https://github.com/DataDog/integrations-core/pull/5710).
* [Fixed] Refactor query_scope utility method. See [#5433](https://github.com/DataDog/integrations-core/pull/5433).

## 3.5.0 / 2019-12-30

* [Fixed] Handle connection closed. See [#5350](https://github.com/DataDog/integrations-core/pull/5350).
* [Added] Add version metadata. See [#4874](https://github.com/DataDog/integrations-core/pull/4874).

## 3.4.0 / 2019-12-02

* [Added] Add lock_type tag to lock metric. See [#5006](https://github.com/DataDog/integrations-core/pull/5006). Thanks [tjwp](https://github.com/tjwp).
* [Added] Extract version utils and use semver for version comparison. See [#4844](https://github.com/DataDog/integrations-core/pull/4844).

## 3.3.0 / 2019-10-30

* [Fixed] Remove multi instance from code. See [#4831](https://github.com/DataDog/integrations-core/pull/4831).
* [Added] Upgrade psycopg2-binary to 2.8.4. See [#4840](https://github.com/DataDog/integrations-core/pull/4840).

## 3.2.1 / 2019-10-11

* [Fixed] Add cache invalidation and better thread lock. See [#4723](https://github.com/DataDog/integrations-core/pull/4723).

## 3.2.0 / 2019-09-10

* [Added] Add schema tag to Lock and Size metrics. See [#3721](https://github.com/DataDog/integrations-core/pull/3721). Thanks [fischaz](https://github.com/fischaz).

## 3.1.3 / 2019-09-04

* [Fixed] Catch statement timeouts correctly. See [#4501](https://github.com/DataDog/integrations-core/pull/4501).

## 3.1.2 / 2019-08-31

* [Fixed] Document new config option. See [#4480](https://github.com/DataDog/integrations-core/pull/4480).

## 3.1.1 / 2019-08-30

* [Fixed] Fix query condition. See [#4484](https://github.com/DataDog/integrations-core/pull/4484). Thanks [dpierce-aledade](https://github.com/dpierce-aledade).

## 3.1.0 / 2019-08-24

* [Added] Make table_count_limit a parameter. See [#3729](https://github.com/DataDog/integrations-core/pull/3729). Thanks [fischaz](https://github.com/fischaz).
* [Added] Add postgresql application name to connection. See [#4295](https://github.com/DataDog/integrations-core/pull/4295).

## 3.0.0 / 2019-07-12

* [Changed] Add SSL support for psycopg2, remove pg8000. See [#4096](https://github.com/DataDog/integrations-core/pull/4096).

## 2.9.1 / 2019-07-04

* [Fixed] Fix tagging for custom queries using custom tags. See [#3930](https://github.com/DataDog/integrations-core/pull/3930).

## 2.9.0 / 2019-06-20

* [Added] Add regex matching for per-relation metrics. See [#3916](https://github.com/DataDog/integrations-core/pull/3916).

## 2.8.0 / 2019-05-14

* [Fixed] Use configuration user for pgsql activity metric. See [#3720](https://github.com/DataDog/integrations-core/pull/3720). Thanks [fischaz](https://github.com/fischaz).
* [Fixed] Fix schema filtering on query relations. See [#3449](https://github.com/DataDog/integrations-core/pull/3449). Thanks [fischaz](https://github.com/fischaz).
* [Added] Upgrade psycopg2-binary to 2.8.2. See [#3649](https://github.com/DataDog/integrations-core/pull/3649).
* [Added] Adhere to code style. See [#3557](https://github.com/DataDog/integrations-core/pull/3557).

## 2.7.0 / 2019-04-05

* [Added] Adds an option to tag metrics with `replication_role`. See [#2929](https://github.com/DataDog/integrations-core/pull/2929).
* [Added] Add `server` tag to metrics and service_check. See [#2928](https://github.com/DataDog/integrations-core/pull/2928).

## 2.6.0 / 2019-03-11

* [Added] Support multiple rows for custom queries. See [#3242](https://github.com/DataDog/integrations-core/pull/3242).

## 2.5.0 / 2019-02-18

* [Added] Finish Python3 Support. See [#2949](https://github.com/DataDog/integrations-core/pull/2949).

## 2.4.0 / 2019-01-04

* [Added] Bump psycopg2-binary version to 2.7.5. See [#2799][1].

## 2.3.0 / 2018-11-30

* [Added] Include db tag with postgresql.locks metrics. See [#2567][2]. Thanks [sj26][3].
* [Added] Support Python 3. See [#2616][4].

## 2.2.3 / 2018-10-14

* [Fixed] Fix version detection for new development releases. See [#2401][5].

## 2.2.2 / 2018-09-11

* [Fixed] Fix version detection for Postgres v10+. See [#2208][6].

## 2.2.1 / 2018-09-06

* [Fixed]  Gracefully handle errors when performing custom_queries. See [#2184][7].
* [Fixed] Gracefully handle failed version regex match. See [#2178][8].

## 2.2.0 / 2018-09-04

* [Added] Add number of "idle in transaction" transactions and open transactions. See [#2118][9].
* [Added] Implement custom_queries and start deprecating custom_metrics. See [#2043][10].
* [Fixed] Fix Postgres version parsing for beta versions. See [#2064][11].
* [Added] Re-enable instance tags for server metrics on Agent version 6. See [#2049][12].
* [Added] Rename dependency psycopg2 to pyscopg2-binary. See [#1842][13].
* [Added] Correcting duplicate metric name, add index_rows_fetched. See [#1762][14].
* [Fixed] Add data files to the wheel package. See [#1727][15].

## 2.1.3 / 2018-06-20

* [Fixed] Fixed postgres verification script. See [#1764][16].

## 2.1.2 / 2018-06-07

* [Fixed] Fix function metrics tagging issue for no-args functions. See [#1452][17]. Thanks [zorgz][18].
* [Security] Update psycopg2 for security fixes. See [#1538][19].

## 2.1.1 / 2018-05-11

* [BUGFIX] Adding db rollback when transaction fails in postgres metrics collection. See[#1193][20].

## 2.1.0 / 2018-03-07

* [BUGFIX] Adding support for postgres 10. See [#1172][21].

## 2.0.0 / 2018-02-13

* [DOC] Adding configuration for log collection in `conf.yaml`
* [DEPRECATING] Starting with agent6 the postgres check no longer tag server wide metrics with instance tags. See [#1073][22]

## 1.2.1 / 2018-02-13

* [BUGFIX] Adding instance tags to service check See [#1042][23]

## 1.2.0 / 2017-11-21

* [IMPROVEMENT] Adding an option to include the default 'postgres' database when gathering stats [#740][24]
* [BUGFIX] Allows `schema` as tag for custom metrics when no schema relations have been defined See[#776][25]

## 1.1.0 / 2017-08-28

* [IMPROVEMENT] Deprecating "postgres.replication_delay_bytes" in favor of "postgresql.replication_delay_bytes". See[#639][26] and [#699][27], thanks to [@Erouan50][28]
* [MINOR] Allow specifying postgres port as string. See [#607][29], thanks [@infothrill][30]

## 1.0.3 / 2017-07-18

* [FEATURE] Collect pg_stat_archiver stats in PG>=9.4.

## 1.0.2 / 2017-06-05

* [IMPROVEMENT] Provide a meaningful error when custom metrics are misconfigured. See [#446][31]

## 1.0.1 / 2017-03-22

* [DEPENDENCY] bump psycopg2 to 2.7.1. See [#295][32].

## 1.0.0 / 2017-03-22

* [FEATURE] adds postgres integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2799
[2]: https://github.com/DataDog/integrations-core/pull/2567
[3]: https://github.com/sj26
[4]: https://github.com/DataDog/integrations-core/pull/2616
[5]: https://github.com/DataDog/integrations-core/pull/2401
[6]: https://github.com/DataDog/integrations-core/pull/2208
[7]: https://github.com/DataDog/integrations-core/pull/2184
[8]: https://github.com/DataDog/integrations-core/pull/2178
[9]: https://github.com/DataDog/integrations-core/pull/2118
[10]: https://github.com/DataDog/integrations-core/pull/2043
[11]: https://github.com/DataDog/integrations-core/pull/2064
[12]: https://github.com/DataDog/integrations-core/pull/2049
[13]: https://github.com/DataDog/integrations-core/pull/1842
[14]: https://github.com/DataDog/integrations-core/pull/1762
[15]: https://github.com/DataDog/integrations-core/pull/1727
[16]: https://github.com/DataDog/integrations-core/pull/1764
[17]: https://github.com/DataDog/integrations-core/pull/1452
[18]: https://github.com/zorgz
[19]: https://github.com/DataDog/integrations-core/pull/1538
[20]:
[21]: https://github.com/DataDog/integrations-core/issues/1172
[22]: https://github.com/DataDog/integrations-core/issues/1073
[23]: https://github.com/DataDog/integrations-core/issues/1042
[24]: https://github.com/DataDog/integrations-core/issues/740
[25]: https://github.com/DataDog/integrations-core/issues/776
[26]: https://github.com/DataDog/integrations-core/issues/639
[27]: https://github.com/DataDog/integrations-core/issues/699
[28]: https://github.com/Erouan50
[29]: https://github.com/DataDog/integrations-core/issues/607
[30]: https://github.com/infothrill
[31]: https://github.com/DataDog/integrations-core/issues/446
[32]: https://github.com/DataDog/integrations-core/issues/295
