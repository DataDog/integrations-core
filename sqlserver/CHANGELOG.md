# CHANGELOG - sqlserver

<!-- towncrier release notes start -->

## 18.0.0 / 2024-10-01

***Changed***:

* Bump minimum version of base check ([#18733](https://github.com/DataDog/integrations-core/pull/18733))

***Added***:

* Bump lxml version for py3.12 E2E tests ([#18637](https://github.com/DataDog/integrations-core/pull/18637))

***Fixed***:

* Fix ODBC config handling for Linux ([#18586](https://github.com/DataDog/integrations-core/pull/18586))

## 17.5.3 / 2024-09-17

***Fixed***:

* Fix ODBC config handling for Linux ([#18586](https://github.com/DataDog/integrations-core/pull/18586))

## 17.5.2 / 2024-08-28 / Agent 7.57.0

***Fixed***:

* Bump lxml to 4.9.4 ([#18244](https://github.com/DataDog/integrations-core/pull/18244))

## 17.5.1 / 2024-08-13

***Fixed***:

* Directly collect the time offset for converting times in SQL Server Agent tables to epoch timestamp through a single, deterministic function. This method avoids calculating the offset as a difference between the server time and UTC time, which led to inaccurate offsets in some cases. ([#18292](https://github.com/DataDog/integrations-core/pull/18292))

## 17.5.0 / 2024-08-09

***Added***:

* Added collection of SQL Server Agent jobs history and activity ([#17787](https://github.com/DataDog/integrations-core/pull/17787))

***Fixed***:

* Fix password obfuscation in OLE DB driver error message when one or more backslashes exist in the password. ([#18203](https://github.com/DataDog/integrations-core/pull/18203))

## 17.4.1 / 2024-08-08 / Agent 7.56.0

***Fixed***:

* Revert "[dbm] fix flapping sqlserver_version" ([#18249](https://github.com/DataDog/integrations-core/pull/18249))

## 17.4.0 / 2024-07-05

***Added***:

* Adding schema collection to sqlserver
  Schema data includes information about the tables, their columns, indexes, foreign keys, and partitions. ([#17258](https://github.com/DataDog/integrations-core/pull/17258))
* Set sqlserver integration default odbc driver to agent embedded msodbcsql18 on Linux platform ([#17729](https://github.com/DataDog/integrations-core/pull/17729))
* Update embedded odbc driver config odbcinist.ini to use msodbcsql 18.3.3.1 ([#17765](https://github.com/DataDog/integrations-core/pull/17765))
* Update dependencies ([#17817](https://github.com/DataDog/integrations-core/pull/17817))

***Fixed***:

* Filter query metrics by database_name if check is configured to a single non-master db ([#17717](https://github.com/DataDog/integrations-core/pull/17717))
* [sqlserver] fix missing sqlserver_version ([#17750](https://github.com/DataDog/integrations-core/pull/17750))
* Hyphen in database name support ([#17775](https://github.com/DataDog/integrations-core/pull/17775))
* Upgrade `azure-identity` dependency ([#17862](https://github.com/DataDog/integrations-core/pull/17862))
* Move sqlserver schema foreign key information to the dependent table. ([#17933](https://github.com/DataDog/integrations-core/pull/17933))

## 17.3.0 / 2024-05-31 / Agent 7.55.0

***Added***:

* Update dependencies ([#17424](https://github.com/DataDog/integrations-core/pull/17424))

***Fixed***:

* Fix Always-On metrics query for replica_failover_mode and replica_failover_readiness. Previously the query returned a cartesian product of rows which could result in incorrect metrics in some cases. ([#17503](https://github.com/DataDog/integrations-core/pull/17503))
* Emit database_instance metadata before collecting metrics
  Decreased database instance collection interval from 1800 seconds to 300 seconds to improve reliability ([#17675](https://github.com/DataDog/integrations-core/pull/17675))

## 17.2.0 / 2024-04-26 / Agent 7.54.0

***Added***:

* Add `sqlserver.database.replica.transaction_delay` metric to report database level replica transaction delays ([#17345](https://github.com/DataDog/integrations-core/pull/17345))
* Add a new config option include_db_fragmentation_metrics_tempdb to skip index fragmentation metrics for tempdb. By default, index fragmentation metrics are NOT be collected for tempdb. ([#17361](https://github.com/DataDog/integrations-core/pull/17361))
* Migrate `SQLServer index usage metrics`,  `SQLServer database index fragmentation metrics` and `SQLServer database backup metrics` to `database_metrics`.
  Increase `SQLServer database index fragmentation metrics` and `SQLServer database backup metrics` default collection interval to 5 mins. ([#17374](https://github.com/DataDog/integrations-core/pull/17374))

***Fixed***:

* Break circular dependency between sqlserver check and connection ([#17275](https://github.com/DataDog/integrations-core/pull/17275))
* Fix missing file stats metrics `sqlserver.files.write_io_stall_queued` and `sqlserver.files.read_io_stall_queued` for sqlserver newer than 2012 and not Azure SQL Database/Azure SQL Managed Instance ([#17299](https://github.com/DataDog/integrations-core/pull/17299))
* Remove db exist check if ignore_missing_database is set to false. In this case throw SQLConnectionError instead of ConfigurationError when database does not exist. ([#17300](https://github.com/DataDog/integrations-core/pull/17300))
* Fix zero value bug for `sqlserver.replica.transaction_delay` metric due to integration wrongly pulling transaction delay performance counter from `SQLServer:Database Mirroring` instead of the the correct object_name `SQLServer:Database Replica` ([#17345](https://github.com/DataDog/integrations-core/pull/17345))
* Fixed a bug where specifying `null` for `custom_metrics` would cause the SQL Server integration to crash ([#17430](https://github.com/DataDog/integrations-core/pull/17430))
* Prevent agent from unsupported USE commands on Azure SQL DBs ([#17448](https://github.com/DataDog/integrations-core/pull/17448))

## 17.1.0 / 2024-03-22 / Agent 7.53.0

***Added***:

* Update custom_queries configuration to support optional collection_interval ([#16957](https://github.com/DataDog/integrations-core/pull/16957))
* Tag SQL Server agent queries with service:datadog-agent ([#17162](https://github.com/DataDog/integrations-core/pull/17162))

***Fixed***:

* Skip index usage collection for tempdb, fixes a blocking query ([#16977](https://github.com/DataDog/integrations-core/pull/16977))
* Fix an issue where logging of obfuscation errors would still hide the statement when it's part of a stored procedure. If the stored procedure obfuscation fails, the `procedure_signature` tag will be set to `__procedure_obfuscation_error__`. ([#17020](https://github.com/DataDog/integrations-core/pull/17020))
* Skip `sqlserver.latches.latch_wait_time metric` on SQL Server version 2012 and 2014. ([#17063](https://github.com/DataDog/integrations-core/pull/17063))
* Update the configuration to include the `metric_prefix` option ([#17065](https://github.com/DataDog/integrations-core/pull/17065))
* Improve service check of autodiscovered databases for the SQL Server integration. The fix prevents agent from creating a connection per database.
  The fix is not applied for Azure hosted databases due to the restriction in switching to dabases within the connection. ([#17139](https://github.com/DataDog/integrations-core/pull/17139))
* Update performance counter base name query to lookup by lowercase counter name ([#17207](https://github.com/DataDog/integrations-core/pull/17207))
* Refactor SQLServer instance connector and adoprovider initialization from configuration.
  The connector/adoprovider config takes precedence in the following order:
  - instance config
  - init config
  - the default connection/adoprovider ([#17245](https://github.com/DataDog/integrations-core/pull/17245))

## 17.0.1 / 2024-02-23 / Agent 7.52.0

***Fixed***:

* Deal with absence of sys.database_files SpaceUsed attribute on Azure SQL Servers ([#16910](https://github.com/DataDog/integrations-core/pull/16910))

## 17.0.0 / 2024-02-16

***Removed***:

* Disables SQL Server metrics on Azure SQL Database instances that rely on cross-database queries. The disabled metrics are:

  * sqlserver.tempdb.file_space_usage.free_space
  * sqlserver.tempdb.file_space_usage.version_store_space
  * sqlserver.tempdb.file_space_usage.internal_object_space
  * sqlserver.tempdb.file_space_usage.user_object_space
  * sqlserver.tempdb.file_space_usage.mixed_extent_space
  * sqlserver.database.backup_count ([#16658](https://github.com/DataDog/integrations-core/pull/16658))

***Added***:

* DBM integrations now defaulted to use new go-sqllexer pkg to obfuscate sql statements ([#16681](https://github.com/DataDog/integrations-core/pull/16681))
* Bump dependencies ([#16858](https://github.com/DataDog/integrations-core/pull/16858))

***Fixed***:

* Improve performance of index_usage_stats query, set default collection interval to 5 minutes and allow interval to be customized. ([#16645](https://github.com/DataDog/integrations-core/pull/16645))
* Require base check that has fix for null characters in query strings ([#16750](https://github.com/DataDog/integrations-core/pull/16750))

## 16.0.2 / 2024-02-23 / Agent 7.51.1

***Fixed***:

* Deal with absence of sys.database_files SpaceUsed attribute on Azure SQL Servers ([#16910](https://github.com/DataDog/integrations-core/pull/16910))

## 16.0.1 / 2024-02-07 / Agent 7.51.0

***Fixed***:

* Replace embedded null characters with empty string in query text ([#16742](https://github.com/DataDog/integrations-core/pull/16742))

## 16.0.0 / 2024-01-05

***Removed***:

* remove pyro4 and serpent dependencies ([#16269](https://github.com/DataDog/integrations-core/pull/16269))

***Changed***:

* Always use the database instance's resolved hostname for metrics regardless of whether dbm is enabled or not. For non-dbm customers, this change
   will result in the host tag having a different value than before. It is possible that dashboards and monitors using the integration's metrics will need to be updated if they relied on the faulty host tagging. ([#16207](https://github.com/DataDog/integrations-core/pull/16207))

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Add stolen memory performance counter ([#16220](https://github.com/DataDog/integrations-core/pull/16220))
* Collect sqlserver.database.files.space_used, and sqlserver.database.is_read_only/is_in_standby metrics. ([#16419](https://github.com/DataDog/integrations-core/pull/16419))
* add new obfuscator options to customize SQL obfuscation and normaliza… ([#16429](https://github.com/DataDog/integrations-core/pull/16429))
* Add ODBC driver support for the SQL Server agent ([#16431](https://github.com/DataDog/integrations-core/pull/16431))
* Add config option to set character limit of stored procedure text ([#16462](https://github.com/DataDog/integrations-core/pull/16462))
* Adds whether a SPID is a user or system process to DBM activity events. ([#16465](https://github.com/DataDog/integrations-core/pull/16465))

***Fixed***:

* Ensure accurate collection of query activity with statement when stored procedure is failed to obfuscate ([#16455](https://github.com/DataDog/integrations-core/pull/16455))
* Skip reporting SqlFractionMetric when base_name is None ([#16469](https://github.com/DataDog/integrations-core/pull/16469))

## 15.2.1 / 2023-12-28 / Agent 7.50.2

***Fixed***:

* Revert "report sql obfuscation error count (#15990)" ([#16439](https://github.com/DataDog/integrations-core/pull/16439))
* fix unexpected exception when reporting sqlserver statements obfuscate xml plan error ([#16461](https://github.com/DataDog/integrations-core/pull/16461))

## 15.2.0 / 2023-11-10 / Agent 7.50.0

***Added***:

* Add support for log shipping monitoring on primary and secondary instances through the `include_primary_log_shipping_metrics` and `include_secondary_log_shipping_metrics` configuration options. ([#16101](https://github.com/DataDog/integrations-core/pull/16101))
* Add obfuscation_mode config option to allow enabling obfuscation with go-sqllexer ([#16125](https://github.com/DataDog/integrations-core/pull/16125)) ([#16125](https://github.com/DataDog/integrations-core/pull/16125))
* Move check config to SQLServerConfig class ([#16130](https://github.com/DataDog/integrations-core/pull/16130))
* Add unit tests to assert every configurable metrics collection ([#16136](https://github.com/DataDog/integrations-core/pull/16136))
* Updated dependencies. ([#16154](https://github.com/DataDog/integrations-core/pull/16154))

***Fixed***:

* Fix `aarch64` compatibility of the `sqlserver` check by downgrading `lxml` to version 4.9.2 ([16080](https://github.com/DataDog/integrations-core/pull/16080)) ([#16080](https://github.com/DataDog/integrations-core/pull/16080))
* Stabilizes the `host` tag on the `sqlserver.can_connect` metric and adds the `connection_host` tag on the same metric. ([#16114](https://github.com/DataDog/integrations-core/pull/16114))
* [SQL Server] - Fix query stats when a query is found in more than one procedure ([#16141](https://github.com/DataDog/integrations-core/pull/16141))

## 15.1.0 / 2023-10-26

***Added***:

* Add support for reporting SQL obfuscation errors ([#15990](https://github.com/DataDog/integrations-core/pull/15990))
* Emit SQLServer metrics queries operation time ([#16066](https://github.com/DataDog/integrations-core/pull/16066))

***Fixed***:

* Properly decode query_hash when statement_text is None ([#15974](https://github.com/DataDog/integrations-core/pull/15974))
* Strip sql comments before parsing procedure name ([#16004](https://github.com/DataDog/integrations-core/pull/16004))
* Bump the `pyodbc` version to 5.0.1 ([#16041](https://github.com/DataDog/integrations-core/pull/16041))
* Fix config option `dbm_enabled` type to ensure it is a boolean ([#16078](https://github.com/DataDog/integrations-core/pull/16078))

## 15.0.3 / 2023-11-08 / Agent 7.49.1

***Fixed***

* Fix `aarch64` compatibility of the `sqlserver` check by downgrading `lxml` to version 4.9.2 ([16080](https://github.com/DataDog/integrations-core/pull/16080))

## 15.0.2 / 2023-10-10 / Agent 7.49.0

***Fixed***:

* Properly decode query_hash when statement_text is None ([#15974](https://github.com/DataDog/integrations-core/pull/15974))

## 15.0.1 / 2023-10-06

***Fixed***

* Set stored procedure collection to `run_sync=False`, fixing the delay in collection of other SQLServer telemetry. ([#15967](https://github.com/DataDog/integrations-core/pull/15967))

## 15.0.0 / 2023-09-29

***Changed***:

* Cache performance counter type to prevent querying for the same counter multiple times (especially for the per-db counters) ([#15714](https://github.com/DataDog/integrations-core/pull/15714))
* Add the `db` tag to every metric also using `database` or `database_name` for consistency ([#15792](https://github.com/DataDog/integrations-core/pull/15792))
* Updates the namespace for version store performance metrics added in ([#15879](https://github.com/DataDog/integrations-core/pull/15879)) to be `sqlserver.transactions.xyz`. ([#15904](https://github.com/DataDog/integrations-core/pull/15904))
* Updates metric documentation in `metadata.csv` to add performance counter information when applicable, and provide a more complete description of available tags per metric. ([15840](https://github.com/DataDog/integrations-core/pull/15840))

***Added***:

* Only collect `SqlDbFileSpaceUsage` metrics for `tempdb` ([#15906](https://github.com/DataDog/integrations-core/pull/15906))
* Add TempDB version store performance counters ([#15879](https://github.com/DataDog/integrations-core/pull/15879))
* Add TempDB page counts metrics ([#15873](https://github.com/DataDog/integrations-core/pull/15873))
* Add `index_name` tag to `.database.avg_fragmentation_in_percent`, `.database.fragment_count`, `.database.avg_fragment_size_in_pages` metrics. Also add a new metric `sqlserver.database.index_page_count`, tagged by `database_name`, `object_name`, `index_id` and `index_name`. ([#15721](https://github.com/DataDog/integrations-core/pull/15721))
* When DBM is enabled, starts collecting stored procedure metrics from sys.dm_exec_procedure_stats at 60s interval (configurable). Also adds the corresponding `procedure_metrics` section to the config file. The new DBM-only metrics are `sqlserver.procedures.count`, `sqlserver.procedures.time`, `sqlserver.procedures.worker_time`, `sqlserver.procedures.physical_reads`, `sqlserver.procedures.logical_reads`, `sqlserver.procedures.logical_writes` and `sqlserver.procedures.spills`. ([#15805](https://github.com/DataDog/integrations-core/pull/15805))
* Add additional SQL Server performance counter metrics ([#15818](https://github.com/DataDog/integrations-core/pull/15818))
* Add Index Usage Metrics for SQL Server ([#15905](https://github.com/DataDog/integrations-core/pull/15905))

***Fixed***:

* Restore the logic for the lookback time in the statement metrics query. It was previously the connection interval * 2, but was removed during a refactor. ([#15857](https://github.com/DataDog/integrations-core/pull/15857))
* Fix type `bytes` is not JSON serializable for dbm events ([#15763](https://github.com/DataDog/integrations-core/pull/15763))
* Fix sqlserver file stats metrics for Azure SQL DB ([#15695](https://github.com/DataDog/integrations-core/pull/15695))
* Fix calculation for performance counters that require a corresponding [base counter type](https://learn.microsoft.com/en-us/windows/win32/wmisdk/base-counter-types) which were previously emitting a constant 100% value (such as `sqlserver.buffer.cache_hit_ratio`). ([#15846](https://github.com/DataDog/integrations-core/pull/15846))

## 14.0.0 / 2023-08-18 / Agent 7.48.0

***Changed***:

* Collect both DBM active sessions and blocking sessions which are sleeping. See ([#14054](https://github.com/DataDog/integrations-core/pull/14054))
* Remove python 2 references from SQL Server integration ([#15606](https://github.com/DataDog/integrations-core/pull/15606))

***Added***:

* Add support for sending `database_instance` metadata ([#15562](https://github.com/DataDog/integrations-core/pull/15562))
* Update dependencies for Agent 7.48 ([#15585](https://github.com/DataDog/integrations-core/pull/15585))
* Support Auth through Azure AD MI / Service Principal ([#15591](https://github.com/DataDog/integrations-core/pull/15591))

## 13.0.0 / 2023-08-10

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))
* Truncate procedure_text in sqlserver activity query ([#15295](https://github.com/DataDog/integrations-core/pull/15295))

***Added***:

* Add support to ingest sys.configurations for SQL Server instances ([#15496](https://github.com/DataDog/integrations-core/pull/15496))
* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Allow for collection of AO metrics for azure sql db ([#15508](https://github.com/DataDog/integrations-core/pull/15508))
* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 12.0.0 / 2023-07-10 / Agent 7.47.0

***Changed***:

* Add a limit on the number of queries in the query metrics payload at the Agent ([#15139](https://github.com/DataDog/integrations-core/pull/15139))
* Do not fetch the full procedure_text in the SQLServer Qstats query ([#15105](https://github.com/DataDog/integrations-core/pull/15105))

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))
* Make cancel() synchronous in DBMAsyncJob ([#14717](https://github.com/DataDog/integrations-core/pull/14717))

***Fixed***:

* sqlserver: remove unused `procedure_text` from metrics payloads ([#15097](https://github.com/DataDog/integrations-core/pull/15097))
* SQL Server query metrics: avoid sending procedure text twice ([#15091](https://github.com/DataDog/integrations-core/pull/15091))
* Move cancel waiting logic to test functions for DBMAsyncJob  ([#14773](https://github.com/DataDog/integrations-core/pull/14773))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 11.2.2 / 2023-06-08 / Agent 7.46.0

***Fixed***:

* Support SQL Server file metrics for Azure SQL DB / MI ([#14679](https://github.com/DataDog/integrations-core/pull/14679))

## 11.2.1 / 2023-06-07

***Fixed***:

* fix sql-server dbm error in certain environments ([#14495](https://github.com/DataDog/integrations-core/pull/14495)) Thanks [it-ito](https://github.com/it-ito).

## 11.2.0 / 2023-05-26

***Added***:

* Add sqlserver engine editition && version to DBM event payloads ([#14499](https://github.com/DataDog/integrations-core/pull/14499))
* [Unified Instance Tagging]: Add cloud_metadata to DBM event payloads ([#14460](https://github.com/DataDog/integrations-core/pull/14460))
* Send resource_type/name for sqlserver integration metrics ([#14320](https://github.com/DataDog/integrations-core/pull/14320))

***Fixed***:

* Exclude model from autodiscovery by default ([#14493](https://github.com/DataDog/integrations-core/pull/14493))
* Rename azure.name configuration key to azure.fully_qualified_domain_name ([#14536](https://github.com/DataDog/integrations-core/pull/14536))
* Properly initialize resolved_hostname so it is set consistently across dbm and default integration metrics ([#14479](https://github.com/DataDog/integrations-core/pull/14479))
* Restore DBM-APM link functionality for SQL Server activity sessions ([#14453](https://github.com/DataDog/integrations-core/pull/14453))

## 11.1.0 / 2023-04-14 / Agent 7.45.0

***Added***:

* Add resolved_hostname to metatdata ([#13639](https://github.com/DataDog/integrations-core/pull/13639))

***Fixed***:

* Fix a typo in the `disable_generic_tags` option description ([#14246](https://github.com/DataDog/integrations-core/pull/14246))
* Increase command_timeout default from 5s to 10s to prevent timeouts on instances with large SQL caches ([#14195](https://github.com/DataDog/integrations-core/pull/14195))
* Do not double emit instance metrics when autodiscovery is enabled ([#14115](https://github.com/DataDog/integrations-core/pull/14115))

## 11.0.2 / 2023-03-21 / Agent 7.44.0

***Fixed***:

* Increase command_timeout default from 5s to 10s to prevent timeouts on instances with large SQL caches ([#14195](https://github.com/DataDog/integrations-core/pull/14195))

## 11.0.1 / 2023-03-08

***Fixed***:

* Do not double emit instance metrics when autodiscovery is enabled ([#14115](https://github.com/DataDog/integrations-core/pull/14115))

## 11.0.0 / 2023-03-03

***Changed***:

* Lower the frequency of query metrics collection ([#14033](https://github.com/DataDog/integrations-core/pull/14033))

***Added***:

* Collect program_name for SQL Server activity ([#13953](https://github.com/DataDog/integrations-core/pull/13953))

## 10.1.3 / 2023-02-01 / Agent 7.43.0

***Fixed***:

* Fix sqlserver.database.state not being sent for all databases ([#13735](https://github.com/DataDog/integrations-core/pull/13735))

## 10.1.2 / 2023-01-26

***Fixed***:

* Bug Fix: Azure SQL DB database name tags properly applied on perf metrics ([#13757](https://github.com/DataDog/integrations-core/pull/13757))

## 10.1.1 / 2023-01-20

***Fixed***:

* Update dependencies ([#13726](https://github.com/DataDog/integrations-core/pull/13726))

## 10.1.0 / 2022-12-09 / Agent 7.42.0

***Added***:

* Add well formatted agent errors on common connection issues for SQL Server ([#13436](https://github.com/DataDog/integrations-core/pull/13436))
* Add procedure name on query metrics/events ([#13484](https://github.com/DataDog/integrations-core/pull/13484))

***Fixed***:

* Fix Query Metrics collection bug where long running queries were missed ([#13335](https://github.com/DataDog/integrations-core/pull/13335))

## 10.0.1 / 2022-12-02 / Agent 7.41.0

***Fixed***:

* Revert "Fix exception thrown when database is null in config" as it was found to introduce a regression ([#13446](https://github.com/DataDog/integrations-core/pull/13446))

## 10.0.0 / 2022-10-28

***Removed***:

* Remove sqlserver tag truncation for metrics ([#13211](https://github.com/DataDog/integrations-core/pull/13211))

***Added***:

* Allow port signal value 0 ([#13135](https://github.com/DataDog/integrations-core/pull/13135))
* Add Agent settings to log original unobfuscated strings ([#12958](https://github.com/DataDog/integrations-core/pull/12958))

***Fixed***:

* Fix exception thrown when database is null in config ([#12882](https://github.com/DataDog/integrations-core/pull/12882))
* Fix Query Metrics query to correct for over-inflated / incorrect SQL Server metrics  ([#13089](https://github.com/DataDog/integrations-core/pull/13089))
* Always cast provided port to str ([#13055](https://github.com/DataDog/integrations-core/pull/13055))

## 9.0.2 / 2022-10-14 / Agent 7.40.0

***Fixed***:

* Fix Query Metrics query to correct for over-inflated / incorrect SQL Server metrics ([#13123](https://github.com/DataDog/integrations-core/pull/13123))

## 9.0.1 / 2022-10-10

***Fixed***:

* Allow users to configure the port as a int or as a string ([#13061](https://github.com/DataDog/integrations-core/pull/13061))

## 9.0.0 / 2022-09-16

***Changed***:

* Use statement_start_offset to extract SQL text being run from Procedure text ([#12613](https://github.com/DataDog/integrations-core/pull/12613))

## 8.1.0 / 2022-08-05 / Agent 7.39.0

***Security***:

* Bump `lxml` package ([#12663](https://github.com/DataDog/integrations-core/pull/12663))

***Added***:

* Add AlwaysOn Availability Group replica status metric ([#12494](https://github.com/DataDog/integrations-core/pull/12494))

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))
* Check for port provided in config ([#12610](https://github.com/DataDog/integrations-core/pull/12610))
* Improve failed connection error messages ([#12533](https://github.com/DataDog/integrations-core/pull/12533))
* Fix documentation for GA DBM support ([#12512](https://github.com/DataDog/integrations-core/pull/12512))
* Support version specific AlwaysOn metrics ([#12424](https://github.com/DataDog/integrations-core/pull/12424))

## 8.0.1 / 2022-06-27 / Agent 7.38.0

***Fixed***:

* Fix engine edition logic bug and simplify configuration for Azure SQL Database  ([#12397](https://github.com/DataDog/integrations-core/pull/12397))
* Support virtual file stats on SQL Server 2012 ([#12094](https://github.com/DataDog/integrations-core/pull/12094))
* Improve handling of encrypted stored procedures ([#12060](https://github.com/DataDog/integrations-core/pull/12060))

## 8.0.0 / 2022-05-15 / Agent 7.37.0

***Changed***:

* Remove execution plan `user_name` attribute ([#12007](https://github.com/DataDog/integrations-core/pull/12007))

***Added***:

* Add AlwaysOn metrics ([#11979](https://github.com/DataDog/integrations-core/pull/11979))
* sqlserver: Add option to keep aliases in sql server (`keep_sql_alias`) ([#12020](https://github.com/DataDog/integrations-core/pull/12020))
* Add support to ingest cloud_metadata for DBM host linking ([#11982](https://github.com/DataDog/integrations-core/pull/11982))
* Add static server OS metrics ([#11864](https://github.com/DataDog/integrations-core/pull/11864))

***Fixed***:

* Don't use connection resiliency for older versions of sqlserver and update valid driver list ([#12026](https://github.com/DataDog/integrations-core/pull/12026))
* Fix uncommented parent options ([#12013](https://github.com/DataDog/integrations-core/pull/12013))
* Upgrade dependencies ([#11958](https://github.com/DataDog/integrations-core/pull/11958))
* Fix missing object_name for index fragmentation metrics ([#11986](https://github.com/DataDog/integrations-core/pull/11986))

## 7.6.2 / 2022-04-20 / Agent 7.36.0

***Fixed***:

* Fix activity and plan host reporting ([#11853](https://github.com/DataDog/integrations-core/pull/11853))

## 7.6.1 / 2022-04-14

***Fixed***:

* Update base version ([#11826](https://github.com/DataDog/integrations-core/pull/11826))

## 7.6.0 / 2022-04-05

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))
* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))
* Add request_status in sqlserver activity query ([#11699](https://github.com/DataDog/integrations-core/pull/11699))
* Add SQL metadata to SQL Server activity events ([#11689](https://github.com/DataDog/integrations-core/pull/11689))
* Add a log line when activity limit is reached ([#11661](https://github.com/DataDog/integrations-core/pull/11661))

***Fixed***:

* Gracefully handle inaccessible database for `sqlserver.files.*` ([#11711](https://github.com/DataDog/integrations-core/pull/11711))
* Fix SQL Server false configuration error ([#11664](https://github.com/DataDog/integrations-core/pull/11664))

## 7.5.0 / 2022-03-15

***Added***:

* Enable SQL metadata collection by default ([#11606](https://github.com/DataDog/integrations-core/pull/11606))

***Fixed***:

* Include SQL metadata in FQT ([#11641](https://github.com/DataDog/integrations-core/pull/11641))

## 7.4.0 / 2022-03-15 / Agent 7.35.0

***Added***:

* Add execution_count and total_elapsed_time fields to SQLServer Samples ([#11652](https://github.com/DataDog/integrations-core/pull/11652))

## 7.3.0 / 2022-03-14

***Added***:

* Add missing wait_resource column for activity collections ([#11638](https://github.com/DataDog/integrations-core/pull/11638))

***Fixed***:

* Fix service check failures on auto discovered dbs failing full check execution ([#11563](https://github.com/DataDog/integrations-core/pull/11563))
* Use remote hostname on all metrics when DBM is enabled ([#11634](https://github.com/DataDog/integrations-core/pull/11634))
* Fix SQLServer activity query, only query for load not transactions ([#11629](https://github.com/DataDog/integrations-core/pull/11629))

## 7.2.0 / 2022-02-19

***Added***:

* Add `pyproject.toml` file ([#11437](https://github.com/DataDog/integrations-core/pull/11437))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))
* remove aggregation by SQL text from query stats query ([#11524](https://github.com/DataDog/integrations-core/pull/11524))

## 7.1.0 / 2022-02-14

***Added***:

* Add ddagenthostname to dbm-metrics payloads ([#11232](https://github.com/DataDog/integrations-core/pull/11232))
* Add recovery_model_desc tag for sqlserver database metrics ([#11210](https://github.com/DataDog/integrations-core/pull/11210)) Thanks [lowlydba](https://github.com/lowlydba).

***Fixed***:

* Disable modified rowcounts in result sets for all connections ([#11486](https://github.com/DataDog/integrations-core/pull/11486))

## 7.0.3 / 2022-02-03 / Agent 7.34.0

***Fixed***:

* Update base version ([#11287](https://github.com/DataDog/integrations-core/pull/11287))

## 7.0.2 / 2022-01-21

***Fixed***:

* Fix license header dates in autogenerated files ([#11187](https://github.com/DataDog/integrations-core/pull/11187))

## 7.0.1 / 2022-01-13

***Fixed***:

* Bump base package dependency ([#11115](https://github.com/DataDog/integrations-core/pull/11115))

## 7.0.0 / 2022-01-08

***Changed***:

* Add `server` default group for all monitor special cases ([#10976](https://github.com/DataDog/integrations-core/pull/10976))
* use read uncommitted isolation level to remove blocking risk ([#10870](https://github.com/DataDog/integrations-core/pull/10870))
* Use dynamic query stats interval and set common request timeout  ([#10848](https://github.com/DataDog/integrations-core/pull/10848))
* improve internal check execution instrumentation ([#10799](https://github.com/DataDog/integrations-core/pull/10799))

***Added***:

* Add improved database file IO metrics and tags ([#10901](https://github.com/DataDog/integrations-core/pull/10901))
* Add statement metadata to events and metrics payload ([#10881](https://github.com/DataDog/integrations-core/pull/10881))
* Add option to disable query metrics secondary aggregates for user and database ([#10975](https://github.com/DataDog/integrations-core/pull/10975))
* Add plan handle to the plan event  ([#10939](https://github.com/DataDog/integrations-core/pull/10939))
* Add the option to set a reported hostname (SQLServer) ([#10688](https://github.com/DataDog/integrations-core/pull/10688))
* Add `enforce_collection_interval_deadline` option to set plan collection deadline ([#10829](https://github.com/DataDog/integrations-core/pull/10829))
* Add current timestamp to SQLServer activity collection ([#10786](https://github.com/DataDog/integrations-core/pull/10786))
* Update SQLServer activity query to get timestamps with the timezone ([#10782](https://github.com/DataDog/integrations-core/pull/10782))
* Add active sessions monitoring support for SQLServer ([#10610](https://github.com/DataDog/integrations-core/pull/10610))

***Fixed***:

* Bump base package ([#11067](https://github.com/DataDog/integrations-core/pull/11067))
* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))
* Fix dangling connection on unhandled exception bug ([#10935](https://github.com/DataDog/integrations-core/pull/10935))
* Improve plan lookup performance ([#10828](https://github.com/DataDog/integrations-core/pull/10828))
* Fix missing ConnectionRetryCount when DSN set ([#10830](https://github.com/DataDog/integrations-core/pull/10830))
* Fix wrong example for MultiSubnetFailover in connection_string example ([#10832](https://github.com/DataDog/integrations-core/pull/10832))
* Improve sqlserver agent query performance for DBM metrics query ([#10810](https://github.com/DataDog/integrations-core/pull/10810))
* Filter databases when using database autodiscovery ([#10416](https://github.com/DataDog/integrations-core/pull/10416))
* Update SQLServer Query Metrics Collection Query to Improve Performance ([#10763](https://github.com/DataDog/integrations-core/pull/10763))
* Add ConnectRetryCount to connection string ([#10738](https://github.com/DataDog/integrations-core/pull/10738))

## 6.2.0 / 2021-12-20 / Agent 7.33.0

***Security***:

* Bump lxml package ([#10904](https://github.com/DataDog/integrations-core/pull/10904))

## 6.1.2 / 2021-11-24

***Fixed***:

* Fix broken unicode support ([#10713](https://github.com/DataDog/integrations-core/pull/10713))
* Enable autocommit for pyodbc ([#10717](https://github.com/DataDog/integrations-core/pull/10717))

## 6.1.1 / 2021-11-19

***Fixed***:

* Fix ADO driver bugs on Windows ([#10637](https://github.com/DataDog/integrations-core/pull/10637))

## 6.1.0 / 2021-11-13

***Added***:

* Update dependencies ([#10580](https://github.com/DataDog/integrations-core/pull/10580))
* Add option to disable autodiscovery database service checks ([#10491](https://github.com/DataDog/integrations-core/pull/10491))

***Fixed***:

* Handle missing DBM metrics columns on older SQL Server versions ([#10594](https://github.com/DataDog/integrations-core/pull/10594))
* Fix sqlserver resolved_hostname by handling comma correctly ([#10592](https://github.com/DataDog/integrations-core/pull/10592))
* Fix memory clerks metrics for sqlserver 2019 ([#10464](https://github.com/DataDog/integrations-core/pull/10464))
* Upgrade datadog checks base to 23.1.5 ([#10468](https://github.com/DataDog/integrations-core/pull/10468))

## 6.0.0 / 2021-10-13

***Changed***:

* Stop sending FCI metrics when not available ([#10395](https://github.com/DataDog/integrations-core/pull/10395))

***Fixed***:

* Account for possible nonetype ([#10257](https://github.com/DataDog/integrations-core/pull/10257))
* DBM check should use its own connection ([#10387](https://github.com/DataDog/integrations-core/pull/10387))
* Remove duplicate names from the list of sql-server metrics to collect ([#10334](https://github.com/DataDog/integrations-core/pull/10334)) Thanks [pedroreys](https://github.com/pedroreys).

## 5.0.2 / 2021-10-26 / Agent 7.32.0

***Fixed***:

* Upgrade datadog checks base to 23.1.5 in sqlserver integration ([#10468](https://github.com/DataDog/integrations-core/pull/10468))

## 5.0.1 / 2021-10-12

***Fixed***:

* DBM check should use its own connection ([#10387](https://github.com/DataDog/integrations-core/pull/10387))

## 5.0.0 / 2021-10-04

***Changed***:

* Implement disable generic tags ([#10290](https://github.com/DataDog/integrations-core/pull/10290))

***Added***:

* Sync configs with new option and bump base requirement ([#10315](https://github.com/DataDog/integrations-core/pull/10315))
* Collect query metrics & plans for Database Monitoring ([#10234](https://github.com/DataDog/integrations-core/pull/10234))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

## 4.1.0 / 2021-08-31

***Added***:

* Add autodiscovered database connection service check ([#9900](https://github.com/DataDog/integrations-core/pull/9900))

## 4.0.0 / 2021-08-22 / Agent 7.31.0

***Changed***:

* Remove messages for integrations for OK service checks ([#9888](https://github.com/DataDog/integrations-core/pull/9888))

## 3.2.0 / 2021-08-12

***Added***:

* Add database file metrics from sys.master_files ([#9812](https://github.com/DataDog/integrations-core/pull/9812))

***Fixed***:

* Capture value error ([#9852](https://github.com/DataDog/integrations-core/pull/9852))

## 3.1.1 / 2021-07-07 / Agent 7.30.0

***Fixed***:

* Do not throw key errors ([#9460](https://github.com/DataDog/integrations-core/pull/9460))

## 3.1.0 / 2021-05-28 / Agent 7.29.0

***Added***:

* Add runtime configuration validation ([#8987](https://github.com/DataDog/integrations-core/pull/8987))

***Fixed***:

* Fix misleading WARN message regarding adoprovider being ignored when using adodbapi connector ([#9412](https://github.com/DataDog/integrations-core/pull/9412))

## 3.0.0 / 2021-03-30 / Agent 7.28.0

***Changed***:

* Utilize time precision function from datadog_checks_base ([#8841](https://github.com/DataDog/integrations-core/pull/8841))

***Added***:

* Upgrade pywin32 on Python 3 ([#8845](https://github.com/DataDog/integrations-core/pull/8845))

***Fixed***:

* Fix autodiscovery tagging ([#9055](https://github.com/DataDog/integrations-core/pull/9055))

## 2.3.8 / 2021-03-16

***Fixed***:

* Improve exception handling for database queries ([#8837](https://github.com/DataDog/integrations-core/pull/8837))
* Ensure delimited identifiers in USE statements ([#8832](https://github.com/DataDog/integrations-core/pull/8832))
* Handle availability replica metrics on earlier versions ([#8830](https://github.com/DataDog/integrations-core/pull/8830))

## 2.3.7 / 2021-03-01 / Agent 7.27.0

***Fixed***:

* Add availability group name tag ([#8658](https://github.com/DataDog/integrations-core/pull/8658))
* Clarify windows user and validate connection options ([#8582](https://github.com/DataDog/integrations-core/pull/8582))
* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 2.3.6 / 2021-01-27 / Agent 7.26.0

***Fixed***:

* Fix cursor execution returning None ([#8481](https://github.com/DataDog/integrations-core/pull/8481))

## 2.3.5 / 2021-01-26

***Fixed***:

* Avoid redundant queries ([#8447](https://github.com/DataDog/integrations-core/pull/8447))

## 2.3.4 / 2021-01-25

***Fixed***:

* Clarify authentication in SQL Server ([#8396](https://github.com/DataDog/integrations-core/pull/8396))

## 2.3.3 / 2021-01-15

***Fixed***:

* Handle offline databases for existence check ([#8374](https://github.com/DataDog/integrations-core/pull/8374))
* Handle overflow error for certain sql queries ([#8366](https://github.com/DataDog/integrations-core/pull/8366))

## 2.3.2 / 2021-01-13

***Fixed***:

* Handle database specific queries for autodiscovery ([#8329](https://github.com/DataDog/integrations-core/pull/8329))
* Small refactor of consts, init and tests ([#8221](https://github.com/DataDog/integrations-core/pull/8221))

## 2.3.1 / 2021-01-05

***Fixed***:

* Add debug messages to SQLServer ([#8278](https://github.com/DataDog/integrations-core/pull/8278))
* Correct default template usage ([#8233](https://github.com/DataDog/integrations-core/pull/8233))

## 2.3.0 / 2020-12-04 / Agent 7.25.0

***Added***:

* Add support for database autodiscovery ([#8115](https://github.com/DataDog/integrations-core/pull/8115))
* Add FCI metrics for SQLServer ([#8056](https://github.com/DataDog/integrations-core/pull/8056))

***Fixed***:

* Handle case sensitivity on database names ([#8113](https://github.com/DataDog/integrations-core/pull/8113))
* Move connection initialization outside init function ([#8064](https://github.com/DataDog/integrations-core/pull/8064))

## 2.2.0 / 2020-11-23

***Added***:

* Add support for custom SQL queries ([#8045](https://github.com/DataDog/integrations-core/pull/8045))
* Add new database backup and fragmentation metrics for SQLServer ([#7998](https://github.com/DataDog/integrations-core/pull/7998))

## 2.1.0 / 2020-10-30 / Agent 7.24.0

***Added***:

* Add AlwaysOn metrics for SQLServer ([#7824](https://github.com/DataDog/integrations-core/pull/7824))
* Support additional performance metrics  ([#7667](https://github.com/DataDog/integrations-core/pull/7667))
* [doc] Add encoding in log config sample ([#7708](https://github.com/DataDog/integrations-core/pull/7708))

## 2.0.0 / 2020-09-21 / Agent 7.23.0

***Changed***:

* SQL Server metrics refactor ([#7551](https://github.com/DataDog/integrations-core/pull/7551))
* Refactor sqlserver connection class and expand test coverage ([#7510](https://github.com/DataDog/integrations-core/pull/7510))
* Update sqlserver to Agent 6 single instance logic ([#7488](https://github.com/DataDog/integrations-core/pull/7488))

***Added***:

* Add Scheduler and Task Metrics for SQL Server ([#5840](https://github.com/DataDog/integrations-core/pull/5840))

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))

## 1.18.1 / 2020-08-10 / Agent 7.22.0

***Fixed***:

* Update logs config service field to optional ([#7209](https://github.com/DataDog/integrations-core/pull/7209))

## 1.18.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Upgrade pywin32 to 228 ([#6980](https://github.com/DataDog/integrations-core/pull/6980))
* Add default `freetds` driver for Docker Agent ([#6636](https://github.com/DataDog/integrations-core/pull/6636))
* Add log support ([#6625](https://github.com/DataDog/integrations-core/pull/6625))

***Fixed***:

* Fix template specs typos ([#6912](https://github.com/DataDog/integrations-core/pull/6912))

## 1.17.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Install `pyodbc` for MacOS and fix local test setup ([#6633](https://github.com/DataDog/integrations-core/pull/6633))
* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

***Fixed***:

* Use agent 6 signature ([#6447](https://github.com/DataDog/integrations-core/pull/6447))

## 1.16.3 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Update deprecated imports ([#6088](https://github.com/DataDog/integrations-core/pull/6088))

## 1.16.2 / 2020-03-10 / Agent 7.18.0

***Fixed***:

* Streamline exception handling ([#6003](https://github.com/DataDog/integrations-core/pull/6003))

## 1.16.1 / 2020-02-22

***Fixed***:

* Fix small capitalization error in log ([#5509](https://github.com/DataDog/integrations-core/pull/5509))

## 1.16.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.15.0 / 2019-12-02 / Agent 7.16.0

***Added***:

* Upgrade pywin32 to 227 ([#5036](https://github.com/DataDog/integrations-core/pull/5036))

## 1.14.0 / 2019-10-11 / Agent 6.15.0

***Added***:

* Upgrade pywin32 to 225 ([#4563](https://github.com/DataDog/integrations-core/pull/4563))

## 1.13.0 / 2019-07-13 / Agent 6.13.0

***Added***:

* Allow SQLNCLI11 provider in SQL server ([#4097](https://github.com/DataDog/integrations-core/pull/4097))

## 1.12.0 / 2019-07-08

***Added***:

* Upgrade dependencies for Python 3.7 binary wheels ([#4030](https://github.com/DataDog/integrations-core/pull/4030))

## 1.11.0 / 2019-05-14 / Agent 6.12.0

***Added***:

* Adhere to code style ([#3567](https://github.com/DataDog/integrations-core/pull/3567))

## 1.10.1 / 2019-04-04 / Agent 6.11.0

***Fixed***:

* Don't ship `pyodbc` on macOS as SQLServer integration is not shipped on macOS ([#3461](https://github.com/DataDog/integrations-core/pull/3461))

## 1.10.0 / 2019-03-29

***Added***:

* Add custom instance tags to storedproc metrics ([#3237](https://github.com/DataDog/integrations-core/pull/3237))

***Fixed***:

* Use execute instead of callproc if using (py)odbc ([#3236](https://github.com/DataDog/integrations-core/pull/3236))

## 1.9.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Support Python 3 ([#3027](https://github.com/DataDog/integrations-core/pull/3027))

## 1.8.1 / 2019-01-04 / Agent 6.9.0

***Fixed***:

* Bump pyodbc for python3.7 compatibility ([#2801](https://github.com/DataDog/integrations-core/pull/2801))

## 1.8.0 / 2018-11-30 / Agent 6.8.0

***Added***:

* Add linux as supported OS ([#2614](https://github.com/DataDog/integrations-core/pull/2614))

***Fixed***:

* Additional debug logging when calling a stored procedure ([#2151](https://github.com/DataDog/integrations-core/pull/2151))
* Use raw string literals when \ is present ([#2465](https://github.com/DataDog/integrations-core/pull/2465))

## 1.7.0 / 2018-10-12 / Agent 6.6.0

***Added***:

* Pin pywin32 dependency ([#2322](https://github.com/DataDog/integrations-core/pull/2322))

## 1.6.0 / 2018-09-04 / Agent 6.5.0

***Added***:

* Support higher query granularity ([#2017](https://github.com/DataDog/integrations-core/pull/2017))
* Add ability to support (via configuration flag) the newer ADO provider ([#1673](https://github.com/DataDog/integrations-core/pull/1673))

***Fixed***:

* Stop leaking db password when a connection is not in the pool ([#2031](https://github.com/DataDog/integrations-core/pull/2031))
* Bump pyro4 and serpent dependencies ([#2007](https://github.com/DataDog/integrations-core/pull/2007))
* Fix for case sensitivity in the `proc_type_mapping` dict. ([#1860](https://github.com/DataDog/integrations-core/pull/1860))
* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.5.0 / 2018-06-20 / Agent 6.4.0

***Added***:

* support object_name metric identifiers ([#1679](https://github.com/DataDog/integrations-core/pull/1679))

## 1.4.0 / 2018-05-11

***Added***:

* Add custom tag support for service checks.

## 1.3.0 / 2018-02-13

***Added***:

* Allow custom connection string to connect ([#1068](https://github.com/DataDog/integrations-core/pull/1068))

## 1.2.1 / 2018-01-10

***Fixed***:

* Allows metric collection from all instances in custom query ([#959](https://github.com/DataDog/integrations-core/issues/959))
* Repair reporting of stats from sys.dm_os_wait_stats ([#975](https://github.com/DataDog/integrations-core/pull/975))

## 1.2.0 / 2017-10-10

***Added***:

* single bulk query of all of metrics, then filter locally ([#573](https://github.com/DataDog/integrations-core/issues/573))

## 1.1.0 / 2017-07-18

***Added***:

* Allow calling custom proc to return metrics, and improve transaction handling ([#357](https://github.com/DataDog/integrations-core/issues/357) and [#456](https://github.com/DataDog/integrations-core/issues/456), thanks [@rlaveycal](https://github)com/rlaveycal)

***Fixed***:

* Fix yaml example file spacing ([#342](https://github.com/DataDog/integrations-core/issues/342), thanks [@themsquared](https://github)com/themsquared)

## 1.0.0 / 2017-03-22

***Added***:

* adds sqlserver integration.
