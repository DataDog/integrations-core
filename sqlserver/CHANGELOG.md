# CHANGELOG - sqlserver

## 10.0.1 / 2022-12-02

* [Fixed] Revert "Fix exception thrown when database is null in config" as it was found to introduce a regression. See [#13446](https://github.com/DataDog/integrations-core/pull/13446).

## 10.0.0 / 2022-10-28

* [Added] Allow port signal value 0. See [#13135](https://github.com/DataDog/integrations-core/pull/13135).
* [Added] Add Agent settings to log original unobfuscated strings. See [#12958](https://github.com/DataDog/integrations-core/pull/12958).
* [Fixed] Fix exception thrown when database is null in config. See [#12882](https://github.com/DataDog/integrations-core/pull/12882).
* [Fixed] Fix Query Metrics query to correct for over-inflated / incorrect SQL Server metrics . See [#13089](https://github.com/DataDog/integrations-core/pull/13089).
* [Fixed] Always cast provided port to str. See [#13055](https://github.com/DataDog/integrations-core/pull/13055).
* [Removed] Remove sqlserver tag truncation for metrics. See [#13211](https://github.com/DataDog/integrations-core/pull/13211).

## 9.0.2 / 2022-10-14

* [Fixed] Fix Query Metrics query to correct for over-inflated / incorrect SQL Server metrics. See [#13123](https://github.com/DataDog/integrations-core/pull/13123).

## 9.0.1 / 2022-10-10

* [Fixed] Allow users to configure the port as a int or as a string. See [#13061](https://github.com/DataDog/integrations-core/pull/13061).

## 9.0.0 / 2022-09-16

* [Changed] Use statement_start_offset to extract SQL text being run from Procedure text. See [#12613](https://github.com/DataDog/integrations-core/pull/12613).

## 8.1.0 / 2022-08-05 / Agent 7.39.0

* [Added] Add AlwaysOn Availability Group replica status metric. See [#12494](https://github.com/DataDog/integrations-core/pull/12494).
* [Fixed] Dependency updates. See [#12653](https://github.com/DataDog/integrations-core/pull/12653).
* [Fixed] Check for port provided in config. See [#12610](https://github.com/DataDog/integrations-core/pull/12610).
* [Fixed] Improve failed connection error messages. See [#12533](https://github.com/DataDog/integrations-core/pull/12533).
* [Fixed] Fix documentation for GA DBM support. See [#12512](https://github.com/DataDog/integrations-core/pull/12512).
* [Fixed] Support version specific AlwaysOn metrics. See [#12424](https://github.com/DataDog/integrations-core/pull/12424).
* [Security] Bump `lxml` package. See [#12663](https://github.com/DataDog/integrations-core/pull/12663).

## 8.0.1 / 2022-06-27 / Agent 7.38.0

* [Fixed] Fix engine edition logic bug and simplify configuration for Azure SQL Database . See [#12397](https://github.com/DataDog/integrations-core/pull/12397).
* [Fixed] Support virtual file stats on SQL Server 2012. See [#12094](https://github.com/DataDog/integrations-core/pull/12094).
* [Fixed] Improve handling of encrypted stored procedures. See [#12060](https://github.com/DataDog/integrations-core/pull/12060).

## 8.0.0 / 2022-05-15 / Agent 7.37.0

* [Added] Add AlwaysOn metrics. See [#11979](https://github.com/DataDog/integrations-core/pull/11979).
* [Added] sqlserver: Add option to keep aliases in sql server (`keep_sql_alias`). See [#12020](https://github.com/DataDog/integrations-core/pull/12020).
* [Added] Add support to ingest cloud_metadata for DBM host linking. See [#11982](https://github.com/DataDog/integrations-core/pull/11982).
* [Added] Add static server OS metrics. See [#11864](https://github.com/DataDog/integrations-core/pull/11864).
* [Fixed] Don't use connection resiliency for older versions of sqlserver and update valid driver list. See [#12026](https://github.com/DataDog/integrations-core/pull/12026).
* [Fixed] Fix uncommented parent options. See [#12013](https://github.com/DataDog/integrations-core/pull/12013).
* [Fixed] Upgrade dependencies. See [#11958](https://github.com/DataDog/integrations-core/pull/11958).
* [Fixed] Fix missing object_name for index fragmentation metrics. See [#11986](https://github.com/DataDog/integrations-core/pull/11986).
* [Changed] Remove execution plan `user_name` attribute. See [#12007](https://github.com/DataDog/integrations-core/pull/12007).

## 7.6.2 / 2022-04-20 / Agent 7.36.0

* [Fixed] Fix activity and plan host reporting. See [#11853](https://github.com/DataDog/integrations-core/pull/11853).

## 7.6.1 / 2022-04-14

* [Fixed] Update base version. See [#11826](https://github.com/DataDog/integrations-core/pull/11826).

## 7.6.0 / 2022-04-05

* [Added] Upgrade dependencies. See [#11726](https://github.com/DataDog/integrations-core/pull/11726).
* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* [Added] Add request_status in sqlserver activity query. See [#11699](https://github.com/DataDog/integrations-core/pull/11699).
* [Added] Add SQL metadata to SQL Server activity events. See [#11689](https://github.com/DataDog/integrations-core/pull/11689).
* [Added] Add a log line when activity limit is reached. See [#11661](https://github.com/DataDog/integrations-core/pull/11661).
* [Fixed] Gracefully handle inaccessible database for `sqlserver.files.*`. See [#11711](https://github.com/DataDog/integrations-core/pull/11711).
* [Fixed] Fix SQL Server false configuration error. See [#11664](https://github.com/DataDog/integrations-core/pull/11664).

## 7.5.0 / 2022-03-15

* [Added] Enable SQL metadata collection by default. See [#11606](https://github.com/DataDog/integrations-core/pull/11606).
* [Fixed] Include SQL metadata in FQT. See [#11641](https://github.com/DataDog/integrations-core/pull/11641).

## 7.4.0 / 2022-03-15 / Agent 7.35.0

* [Added] Add execution_count and total_elapsed_time fields to SQLServer Samples. See [#11652](https://github.com/DataDog/integrations-core/pull/11652).

## 7.3.0 / 2022-03-14

* [Added] Add missing wait_resource column for activity collections. See [#11638](https://github.com/DataDog/integrations-core/pull/11638).
* [Fixed] Fix service check failures on auto discovered dbs failing full check execution. See [#11563](https://github.com/DataDog/integrations-core/pull/11563).
* [Fixed] Use remote hostname on all metrics when DBM is enabled. See [#11634](https://github.com/DataDog/integrations-core/pull/11634).
* [Fixed] Fix SQLServer activity query, only query for load not transactions. See [#11629](https://github.com/DataDog/integrations-core/pull/11629).

## 7.2.0 / 2022-02-19

* [Added] Add `pyproject.toml` file. See [#11437](https://github.com/DataDog/integrations-core/pull/11437).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* [Fixed] remove aggregation by SQL text from query stats query. See [#11524](https://github.com/DataDog/integrations-core/pull/11524).

## 7.1.0 / 2022-02-14

* [Added] Add ddagenthostname to dbm-metrics payloads. See [#11232](https://github.com/DataDog/integrations-core/pull/11232).
* [Added] Add recovery_model_desc tag for sqlserver database metrics. See [#11210](https://github.com/DataDog/integrations-core/pull/11210). Thanks [lowlydba](https://github.com/lowlydba).
* [Fixed] Disable modified rowcounts in result sets for all connections. See [#11486](https://github.com/DataDog/integrations-core/pull/11486).

## 7.0.3 / 2022-02-03 / Agent 7.34.0

* [Fixed] Update base version. See [#11287](https://github.com/DataDog/integrations-core/pull/11287).

## 7.0.2 / 2022-01-21

* [Fixed] Fix license header dates in autogenerated files. See [#11187](https://github.com/DataDog/integrations-core/pull/11187).

## 7.0.1 / 2022-01-13

* [Fixed] Bump base package dependency. See [#11115](https://github.com/DataDog/integrations-core/pull/11115).

## 7.0.0 / 2022-01-08

* [Added] Add improved database file IO metrics and tags. See [#10901](https://github.com/DataDog/integrations-core/pull/10901).
* [Added] Add statement metadata to events and metrics payload. See [#10881](https://github.com/DataDog/integrations-core/pull/10881).
* [Added] Add option to disable query metrics secondary aggregates for user and database. See [#10975](https://github.com/DataDog/integrations-core/pull/10975).
* [Added] Add plan handle to the plan event . See [#10939](https://github.com/DataDog/integrations-core/pull/10939).
* [Added] Add the option to set a reported hostname (SQLServer). See [#10688](https://github.com/DataDog/integrations-core/pull/10688).
* [Added] Add `enforce_collection_interval_deadline` option to set plan collection deadline. See [#10829](https://github.com/DataDog/integrations-core/pull/10829).
* [Added] Add current timestamp to SQLServer activity collection. See [#10786](https://github.com/DataDog/integrations-core/pull/10786).
* [Added] Update SQLServer activity query to get timestamps with the timezone. See [#10782](https://github.com/DataDog/integrations-core/pull/10782).
* [Added] Add active sessions monitoring support for SQLServer. See [#10610](https://github.com/DataDog/integrations-core/pull/10610).
* [Fixed] Bump base package. See [#11067](https://github.com/DataDog/integrations-core/pull/11067).
* [Fixed] Add comment to autogenerated model files. See [#10945](https://github.com/DataDog/integrations-core/pull/10945).
* [Fixed] Fix dangling connection on unhandled exception bug. See [#10935](https://github.com/DataDog/integrations-core/pull/10935).
* [Fixed] Improve plan lookup performance. See [#10828](https://github.com/DataDog/integrations-core/pull/10828).
* [Fixed] Fix missing ConnectionRetryCount when DSN set. See [#10830](https://github.com/DataDog/integrations-core/pull/10830).
* [Fixed] Fix wrong example for MultiSubnetFailover in connection_string example. See [#10832](https://github.com/DataDog/integrations-core/pull/10832).
* [Fixed] Improve sqlserver agent query performance for DBM metrics query. See [#10810](https://github.com/DataDog/integrations-core/pull/10810).
* [Fixed] Filter databases when using database autodiscovery. See [#10416](https://github.com/DataDog/integrations-core/pull/10416).
* [Fixed] Update SQLServer Query Metrics Collection Query to Improve Performance. See [#10763](https://github.com/DataDog/integrations-core/pull/10763).
* [Fixed] Add ConnectRetryCount to connection string. See [#10738](https://github.com/DataDog/integrations-core/pull/10738).
* [Changed] Add `server` default group for all monitor special cases. See [#10976](https://github.com/DataDog/integrations-core/pull/10976).
* [Changed] use read uncommitted isolation level to remove blocking risk. See [#10870](https://github.com/DataDog/integrations-core/pull/10870).
* [Changed] Use dynamic query stats interval and set common request timeout . See [#10848](https://github.com/DataDog/integrations-core/pull/10848).
* [Changed] improve internal check execution instrumentation. See [#10799](https://github.com/DataDog/integrations-core/pull/10799).

## 6.2.0 / 2021-12-20 / Agent 7.33.0

* [Security] Bump lxml package. See [#10904](https://github.com/DataDog/integrations-core/pull/10904).

## 6.1.2 / 2021-11-24

* [Fixed] Fix broken unicode support. See [#10713](https://github.com/DataDog/integrations-core/pull/10713).
* [Fixed] Enable autocommit for pyodbc. See [#10717](https://github.com/DataDog/integrations-core/pull/10717).

## 6.1.1 / 2021-11-19

* [Fixed] Fix ADO driver bugs on Windows. See [#10637](https://github.com/DataDog/integrations-core/pull/10637).

## 6.1.0 / 2021-11-13

* [Added] Update dependencies. See [#10580](https://github.com/DataDog/integrations-core/pull/10580).
* [Added] Add option to disable autodiscovery database service checks. See [#10491](https://github.com/DataDog/integrations-core/pull/10491).
* [Fixed] Handle missing DBM metrics columns on older SQL Server versions. See [#10594](https://github.com/DataDog/integrations-core/pull/10594).
* [Fixed] Fix sqlserver resolved_hostname by handling comma correctly. See [#10592](https://github.com/DataDog/integrations-core/pull/10592).
* [Fixed] Fix memory clerks metrics for sqlserver 2019. See [#10464](https://github.com/DataDog/integrations-core/pull/10464).
* [Fixed] Upgrade datadog checks base to 23.1.5. See [#10468](https://github.com/DataDog/integrations-core/pull/10468).

## 6.0.0 / 2021-10-13

* [Fixed] Account for possible nonetype. See [#10257](https://github.com/DataDog/integrations-core/pull/10257).
* [Fixed] DBM check should use its own connection. See [#10387](https://github.com/DataDog/integrations-core/pull/10387).
* [Fixed] Remove duplicate names from the list of sql-server metrics to collect. See [#10334](https://github.com/DataDog/integrations-core/pull/10334). Thanks [pedroreys](https://github.com/pedroreys).
* [Changed] Stop sending FCI metrics when not available. See [#10395](https://github.com/DataDog/integrations-core/pull/10395).

## 5.0.2 / 2021-10-26 / Agent 7.32.0

* [Fixed] Upgrade datadog checks base to 23.1.5 in sqlserver integration. See [#10468](https://github.com/DataDog/integrations-core/pull/10468).

## 5.0.1 / 2021-10-12

* [Fixed] DBM check should use its own connection. See [#10387](https://github.com/DataDog/integrations-core/pull/10387).

## 5.0.0 / 2021-10-04

* [Added] Sync configs with new option and bump base requirement. See [#10315](https://github.com/DataDog/integrations-core/pull/10315).
* [Added] Collect query metrics & plans for Database Monitoring. See [#10234](https://github.com/DataDog/integrations-core/pull/10234).
* [Added] Disable generic tags. See [#10027](https://github.com/DataDog/integrations-core/pull/10027).
* [Changed] Implement disable generic tags. See [#10290](https://github.com/DataDog/integrations-core/pull/10290).

## 4.1.0 / 2021-08-31

* [Added] Add autodiscovered database connection service check. See [#9900](https://github.com/DataDog/integrations-core/pull/9900).

## 4.0.0 / 2021-08-22 / Agent 7.31.0

* [Changed] Remove messages for integrations for OK service checks. See [#9888](https://github.com/DataDog/integrations-core/pull/9888).

## 3.2.0 / 2021-08-12

* [Added] Add database file metrics from sys.master_files. See [#9812](https://github.com/DataDog/integrations-core/pull/9812).
* [Fixed] Capture value error. See [#9852](https://github.com/DataDog/integrations-core/pull/9852).

## 3.1.1 / 2021-07-07 / Agent 7.30.0

* [Fixed] Do not throw key errors. See [#9460](https://github.com/DataDog/integrations-core/pull/9460).

## 3.1.0 / 2021-05-28 / Agent 7.29.0

* [Added] Add runtime configuration validation. See [#8987](https://github.com/DataDog/integrations-core/pull/8987).
* [Fixed] Fix misleading WARN message regarding adoprovider being ignored when using adodbapi connector. See [#9412](https://github.com/DataDog/integrations-core/pull/9412).

## 3.0.0 / 2021-03-30 / Agent 7.28.0

* [Added] Upgrade pywin32 on Python 3. See [#8845](https://github.com/DataDog/integrations-core/pull/8845).
* [Fixed] Fix autodiscovery tagging. See [#9055](https://github.com/DataDog/integrations-core/pull/9055).
* [Changed] Utilize time precision function from datadog_checks_base. See [#8841](https://github.com/DataDog/integrations-core/pull/8841).

## 2.3.8 / 2021-03-16

* [Fixed] Improve exception handling for database queries. See [#8837](https://github.com/DataDog/integrations-core/pull/8837).
* [Fixed] Ensure delimited identifiers in USE statements. See [#8832](https://github.com/DataDog/integrations-core/pull/8832).
* [Fixed] Handle availability replica metrics on earlier versions. See [#8830](https://github.com/DataDog/integrations-core/pull/8830).

## 2.3.7 / 2021-03-01 / Agent 7.27.0

* [Fixed] Add availability group name tag. See [#8658](https://github.com/DataDog/integrations-core/pull/8658).
* [Fixed] Clarify windows user and validate connection options. See [#8582](https://github.com/DataDog/integrations-core/pull/8582).
* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 2.3.6 / 2021-01-27 / Agent 7.26.0

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

* [Fixed] Bump pyodbc for python3.7 compatibility. See [#2801](https://github.com/DataDog/integrations-core/pull/2801).

## 1.8.0 / 2018-11-30 / Agent 6.8.0

* [Added] Add linux as supported OS. See [#2614](https://github.com/DataDog/integrations-core/pull/2614).
* [Fixed] Additional debug logging when calling a stored procedure. See [#2151](https://github.com/DataDog/integrations-core/pull/2151).
* [Fixed] Use raw string literals when \ is present. See [#2465](https://github.com/DataDog/integrations-core/pull/2465).

## 1.7.0 / 2018-10-12 / Agent 6.6.0

* [Added] Pin pywin32 dependency. See [#2322](https://github.com/DataDog/integrations-core/pull/2322).

## 1.6.0 / 2018-09-04 / Agent 6.5.0

* [Added] Support higher query granularity. See [#2017](https://github.com/DataDog/integrations-core/pull/2017).
* [Added] Add ability to support (via configuration flag) the newer ADO provider. See [#1673](https://github.com/DataDog/integrations-core/pull/1673).
* [Fixed] Stop leaking db password when a connection is not in the pool. See [#2031](https://github.com/DataDog/integrations-core/pull/2031).
* [Fixed] Bump pyro4 and serpent dependencies. See [#2007](https://github.com/DataDog/integrations-core/pull/2007).
* [Fixed] Fix for case sensitivity in the `proc_type_mapping` dict.. See [#1860](https://github.com/DataDog/integrations-core/pull/1860).
* [Fixed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).

## 1.5.0 / 2018-06-20 / Agent 6.4.0

* [Added] support object_name metric identifiers. See [#1679](https://github.com/DataDog/integrations-core/pull/1679).

## 1.4.0 / 2018-05-11

* [FEATURE] Add custom tag support for service checks.

## 1.3.0 / 2018-02-13

* [IMPROVEMENT] Allow custom connection string to connect. See [#1068](https://github.com/DataDog/integrations-core/pull/1065).

## 1.2.1 / 2018-01-10

* [BUGFIX] Allows metric collection from all instances in custom query. See [#959](https://github.com/DataDog/integrations-core/issues/959).
* [BUGFIX] Repair reporting of stats from sys.dm_os_wait_stats. See [#975](https://github.com/DataDog/integrations-core/pull/975).

## 1.2.0 / 2017-10-10

* [FEATURE] single bulk query of all of metrics, then filter locally. See [#573](https://github.com/DataDog/integrations-core/issues/573).

## 1.1.0 / 2017-07-18

* [FEATURE] Allow calling custom proc to return metrics, and improve transaction handling. See [#357](https://github.com/DataDog/integrations-core/issues/357) and [#456](https://github.com/DataDog/integrations-core/issues/456), thanks [@rlaveycal](https://github.com/rlaveycal)
* [SANITY] Fix yaml example file spacing. See [#342](https://github.com/DataDog/integrations-core/issues/342), thanks [@themsquared](https://github.com/themsquared)

## 1.0.0 / 2017-03-22

* [FEATURE] adds sqlserver integration.
