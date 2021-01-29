# CHANGELOG - sqlserver

## 2.3.6 / 2021-01-27

* [Fixed] Fix cursor execution returning None. See [#8481](https://github.com/DataDog/integrations-core/pull/8481).

## 2.3.5 / 2021-01-26

* [Fixed] Avoid redundant queries. See [#8447](https://github.com/DataDog/integrations-core/pull/8447).

## 2.3.4 / 2021-01-25

* [Fixed] Clarify authentication in SQL Server. See [#8396](https://github.com/DataDog/integrations-core/pull/8396).

## 2.3.3 / 2021-01-15

* [Fixed] Handle offline databases for existence check. See [#8374](https://github.com/DataDog/integrations-core/pull/8374).
* [Fixed] Handle overflow error for certain sql queries. See [#8366](https://github.com/DataDog/integrations-core/pull/8366).

## 2.3.2 / 2021-01-13

* [Fixed] Handle database specific queries for autodiscovery. See [#8329](https://github.com/DataDog/integrations-core/pull/8329).
* [Fixed] Small refactor of consts, init and tests. See [#8221](https://github.com/DataDog/integrations-core/pull/8221).

## 2.3.1 / 2021-01-05

* [Fixed] Add debug messages to SQLServer. See [#8278](https://github.com/DataDog/integrations-core/pull/8278).
* [Fixed] Correct default template usage. See [#8233](https://github.com/DataDog/integrations-core/pull/8233).

## 2.3.0 / 2020-12-04 / Agent 7.25.0

* [Added] Add support for database autodiscovery. See [#8115](https://github.com/DataDog/integrations-core/pull/8115).
* [Added] Add FCI metrics for SQLServer. See [#8056](https://github.com/DataDog/integrations-core/pull/8056).
* [Fixed] Handle case sensitivity on database names. See [#8113](https://github.com/DataDog/integrations-core/pull/8113).
* [Fixed] Move connection initialization outside init function. See [#8064](https://github.com/DataDog/integrations-core/pull/8064).

## 2.2.0 / 2020-11-23

* [Added] Add support for custom SQL queries. See [#8045](https://github.com/DataDog/integrations-core/pull/8045).
* [Added] Add new database backup and fragmentation metrics for SQLServer. See [#7998](https://github.com/DataDog/integrations-core/pull/7998).

## 2.1.0 / 2020-10-30 / Agent 7.24.0

* [Added] Add AlwaysOn metrics for SQLServer. See [#7824](https://github.com/DataDog/integrations-core/pull/7824).
* [Added] Support additional performance metrics . See [#7667](https://github.com/DataDog/integrations-core/pull/7667).
* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 2.0.0 / 2020-09-21 / Agent 7.23.0

* [Added] Add Scheduler and Task Metrics for SQL Server. See [#5840](https://github.com/DataDog/integrations-core/pull/5840).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).
* [Changed] SQL Server metrics refactor. See [#7551](https://github.com/DataDog/integrations-core/pull/7551).
* [Changed] Refactor sqlserver connection class and expand test coverage. See [#7510](https://github.com/DataDog/integrations-core/pull/7510).
* [Changed] Update sqlserver to Agent 6 single instance logic. See [#7488](https://github.com/DataDog/integrations-core/pull/7488).

## 1.18.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).

## 1.18.0 / 2020-06-29 / Agent 7.21.0

* [Added] Upgrade pywin32 to 228. See [#6980](https://github.com/DataDog/integrations-core/pull/6980).
* [Added] Add default `freetds` driver for Docker Agent. See [#6636](https://github.com/DataDog/integrations-core/pull/6636).
* [Added] Add log support. See [#6625](https://github.com/DataDog/integrations-core/pull/6625).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).

## 1.17.0 / 2020-05-17 / Agent 7.20.0

* [Added] Install `pyodbc` for MacOS and fix local test setup. See [#6633](https://github.com/DataDog/integrations-core/pull/6633).
* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Fixed] Use agent 6 signature. See [#6447](https://github.com/DataDog/integrations-core/pull/6447).

## 1.16.3 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 1.16.2 / 2020-03-10 / Agent 7.18.0

* [Fixed] Streamline exception handling. See [#6003](https://github.com/DataDog/integrations-core/pull/6003).

## 1.16.1 / 2020-02-22

* [Fixed] Fix small capitalization error in log. See [#5509](https://github.com/DataDog/integrations-core/pull/5509).

## 1.16.0 / 2020-01-13 / Agent 7.17.0

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.15.0 / 2019-12-02 / Agent 7.16.0

* [Added] Upgrade pywin32 to 227. See [#5036](https://github.com/DataDog/integrations-core/pull/5036).

## 1.14.0 / 2019-10-11 / Agent 6.15.0

* [Added] Upgrade pywin32 to 225. See [#4563](https://github.com/DataDog/integrations-core/pull/4563).

## 1.13.0 / 2019-07-13 / Agent 6.13.0

* [Added] Allow SQLNCLI11 provider in SQL server. See [#4097](https://github.com/DataDog/integrations-core/pull/4097).

## 1.12.0 / 2019-07-08

* [Added] Upgrade dependencies for Python 3.7 binary wheels. See [#4030](https://github.com/DataDog/integrations-core/pull/4030).

## 1.11.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3567](https://github.com/DataDog/integrations-core/pull/3567).

## 1.10.1 / 2019-04-04 / Agent 6.11.0

* [Fixed] Don't ship `pyodbc` on macOS as SQLServer integration is not shipped on macOS. See [#3461](https://github.com/DataDog/integrations-core/pull/3461).

## 1.10.0 / 2019-03-29

* [Added] Add custom instance tags to storedproc metrics. See [#3237](https://github.com/DataDog/integrations-core/pull/3237).
* [Fixed] Use execute instead of callproc if using (py)odbc. See [#3236](https://github.com/DataDog/integrations-core/pull/3236).

## 1.9.0 / 2019-02-18 / Agent 6.10.0

* [Added] Support Python 3. See [#3027](https://github.com/DataDog/integrations-core/pull/3027).

## 1.8.1 / 2019-01-04 / Agent 6.9.0

* [Fixed] Bump pyodbc for python3.7 compatibility. See [#2801][1].

## 1.8.0 / 2018-11-30 / Agent 6.8.0

* [Added] Add linux as supported OS. See [#2614][2].
* [Fixed] Additional debug logging when calling a stored procedure. See [#2151][3].
* [Fixed] Use raw string literals when \ is present. See [#2465][4].

## 1.7.0 / 2018-10-12 / Agent 6.6.0

* [Added] Pin pywin32 dependency. See [#2322][5].

## 1.6.0 / 2018-09-04 / Agent 6.5.0

* [Added] Support higher query granularity. See [#2017][6].
* [Added] Add ability to support (via configuration flag) the newer ADO provider. See [#1673][7].
* [Fixed] Stop leaking db password when a connection is not in the pool. See [#2031][8].
* [Fixed] Bump pyro4 and serpent dependencies. See [#2007][9].
* [Fixed] Fix for case sensitivity in the `proc_type_mapping` dict.. See [#1860][10].
* [Fixed] Add data files to the wheel package. See [#1727][11].

## 1.5.0 / 2018-06-20 / Agent 6.4.0

* [Added] support object_name metric identifiers. See [#1679][12].

## 1.4.0 / 2018-05-11

* [FEATURE] Add custom tag support for service checks.

## 1.3.0 / 2018-02-13

* [IMPROVEMENT] Allow custom connection string to connect. See [#1068][13].

## 1.2.1 / 2018-01-10

* [BUGFIX] Allows metric collection from all instances in custom query. See [#959][14].
* [BUGFIX] Repair reporting of stats from sys.dm_os_wait_stats. See [#975][15].

## 1.2.0 / 2017-10-10

* [FEATURE] single bulk query of all of metrics, then filter locally. See [#573][16].

## 1.1.0 / 2017-07-18

* [FEATURE] Allow calling custom proc to return metrics, and improve transaction handling. See [#357][17] and [#456][18], thanks [@rlaveycal][19]
* [SANITY] Fix yaml example file spacing. See [#342][20], thanks [@themsquared][21]

## 1.0.0 / 2017-03-22

* [FEATURE] adds sqlserver integration.

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2801
[2]: https://github.com/DataDog/integrations-core/pull/2614
[3]: https://github.com/DataDog/integrations-core/pull/2151
[4]: https://github.com/DataDog/integrations-core/pull/2465
[5]: https://github.com/DataDog/integrations-core/pull/2322
[6]: https://github.com/DataDog/integrations-core/pull/2017
[7]: https://github.com/DataDog/integrations-core/pull/1673
[8]: https://github.com/DataDog/integrations-core/pull/2031
[9]: https://github.com/DataDog/integrations-core/pull/2007
[10]: https://github.com/DataDog/integrations-core/pull/1860
[11]: https://github.com/DataDog/integrations-core/pull/1727
[12]: https://github.com/DataDog/integrations-core/pull/1679
[13]: https://github.com/DataDog/integrations-core/pull/1065
[14]: https://github.com/DataDog/integrations-core/issues/959
[15]: https://github.com/DataDog/integrations-core/pull/975
[16]: https://github.com/DataDog/integrations-core/issues/573
[17]: https://github.com/DataDog/integrations-core/issues/357
[18]: https://github.com/DataDog/integrations-core/issues/456
[19]: https://github.com/rlaveycal
[20]: https://github.com/DataDog/integrations-core/issues/342
[21]: https://github.com/themsquared
