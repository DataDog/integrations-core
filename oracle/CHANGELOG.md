# CHANGELOG - oracle

<!-- towncrier release notes start -->

## 5.2.0 / 2024-03-22 / Agent 7.53.0

***Deprecated***:

* Automatically load Oracle core check instead of Python integration. Deprecating Oracle Python integration and replacing it with the core check. ([#17248](https://github.com/DataDog/integrations-core/pull/17248))

***Added***:

* Update custom_queries configuration to support optional collection_interval ([#16957](https://github.com/DataDog/integrations-core/pull/16957))
* Bump the min base check version to 36.5.0 ([#17197](https://github.com/DataDog/integrations-core/pull/17197))

***Fixed***:

* Support custom metric_prefix in QueryExecutor and remove manual fix of metric_prefix ([#16958](https://github.com/DataDog/integrations-core/pull/16958))
* Update the configuration to include the `metric_prefix` option ([#17065](https://github.com/DataDog/integrations-core/pull/17065))

## 5.1.1 / 2024-01-10 / Agent 7.51.0

***Fixed***:

* Properly drop support for Python 2 ([#16589](https://github.com/DataDog/integrations-core/pull/16589))

## 5.1.0 / 2024-01-05

***Added***:

* Bump the Python version from py3.9 to py3.11 ([#15997](https://github.com/DataDog/integrations-core/pull/15997))
* Update dependencies ([#16502](https://github.com/DataDog/integrations-core/pull/16502))

## 5.0.0 / 2023-08-10 / Agent 7.48.0

***Changed***:

* Bump the minimum base check version ([#15427](https://github.com/DataDog/integrations-core/pull/15427))

***Added***:

* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))

## 4.2.0 / 2023-07-10 / Agent 7.47.0

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))

***Fixed***:

* Downgrade requirements to 3.8 ([#14711](https://github.com/DataDog/integrations-core/pull/14711))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 4.1.1 / 2023-05-26 / Agent 7.46.0

***Fixed***:

* Update dependencies ([#14594](https://github.com/DataDog/integrations-core/pull/14594))

## 4.1.0 / 2023-04-14 / Agent 7.45.0

***Added***:

* Update dependencies ([#14357](https://github.com/DataDog/integrations-core/pull/14357))
* Add thick mode for oracledb ([#14166](https://github.com/DataDog/integrations-core/pull/14166))

***Fixed***:

* Update GV$PROCESS query ([#14143](https://github.com/DataDog/integrations-core/pull/14143)) Thanks [jake-condello](https://github.com/jake-condello).

## 4.0.1 / 2023-01-20 / Agent 7.43.0

***Fixed***:

* Do not add `can_use_jdbc` to `check_initializations` ([#13521](https://github.com/DataDog/integrations-core/pull/13521))

## 4.0.0 / 2022-12-09 / Agent 7.42.0

***Changed***:

* Update Oracle check to use python-oracledb library ([#13298](https://github.com/DataDog/integrations-core/pull/13298))

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))
* Skip empty columns when metric_prefix is used for custom queries ([#13234](https://github.com/DataDog/integrations-core/pull/13234))

## 3.9.5 / 2022-08-05 / Agent 7.39.0

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))

## 3.9.4 / 2022-05-15 / Agent 7.37.0

***Fixed***:

* Add a lock around jdbc connection ([#11877](https://github.com/DataDog/integrations-core/pull/11877))
* Do not close closed connection ([#11874](https://github.com/DataDog/integrations-core/pull/11874))

## 3.9.3 / 2022-04-14 / Agent 7.36.0

***Fixed***:

* Handle NoneType protocol validation ([#11837](https://github.com/DataDog/integrations-core/pull/11837))

## 3.9.2 / 2022-04-11

***Fixed***:

* Ensure connect raises exception on failure ([#11787](https://github.com/DataDog/integrations-core/pull/11787))

## 3.9.1 / 2022-04-07

***Fixed***:

* Fix protocol validation ([#11791](https://github.com/DataDog/integrations-core/pull/11791))

## 3.9.0 / 2022-04-05

***Added***:

* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))

## 3.8.0 / 2022-03-25

***Added***:

* Add metric_patterns options to filter all metric submission by a list of regexes ([#11695](https://github.com/DataDog/integrations-core/pull/11695))

***Fixed***:

* Properly report a critical service check status if connection to database fails using the Oracle client ([#11691](https://github.com/DataDog/integrations-core/pull/11691))
* Fix validation for the `protocol` param ([#11675](https://github.com/DataDog/integrations-core/pull/11675))

## 3.7.0 / 2022-02-19 / Agent 7.35.0

***Added***:

* Add `pyproject.toml` file ([#11410](https://github.com/DataDog/integrations-core/pull/11410))

***Fixed***:

* Fix namespace packaging on Python 2 ([#11532](https://github.com/DataDog/integrations-core/pull/11532))

## 3.6.0 / 2022-01-08 / Agent 7.34.0

***Added***:

* Add TCPS support for Oracle DB ([#10591](https://github.com/DataDog/integrations-core/pull/10591))

***Fixed***:

* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))

## 3.5.0 / 2021-10-04 / Agent 7.32.0

***Added***:

* Sync configs with new option and bump base requirement ([#10315](https://github.com/DataDog/integrations-core/pull/10315))
* Update dependencies ([#10258](https://github.com/DataDog/integrations-core/pull/10258))
* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

***Fixed***:

* Add server as generic tag ([#10100](https://github.com/DataDog/integrations-core/pull/10100))

## 3.4.0 / 2021-09-02

***Added***:

* Add new service check `oracle.can_query` ([#10004](https://github.com/DataDog/integrations-core/pull/10004))

## 3.3.4 / 2021-08-04 / Agent 7.31.0

***Fixed***:

* Create dns with instant client ([#9712](https://github.com/DataDog/integrations-core/pull/9712))

## 3.3.3 / 2021-07-30

***Fixed***:

* Explicitly close connection after query error ([#9800](https://github.com/DataDog/integrations-core/pull/9800))

## 3.3.2 / 2021-07-22 / Agent 7.30.0

***Fixed***:

* Properly allow deprecated required config ([#9750](https://github.com/DataDog/integrations-core/pull/9750))
* Bump base package dependency ([#9666](https://github.com/DataDog/integrations-core/pull/9666))

## 3.3.1 / 2021-07-12

***Fixed***:

* Bump base package dependency ([#9666](https://github.com/DataDog/integrations-core/pull/9666))
* Dont use connection string for client ([#9219](https://github.com/DataDog/integrations-core/pull/9219))

## 3.3.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Add runtime configuration validation ([#8966](https://github.com/DataDog/integrations-core/pull/8966))

## 3.2.0 / 2021-03-07 / Agent 7.27.0

***Added***:

* Upgrade JPype1 to 1.2.1 ([#8479](https://github.com/DataDog/integrations-core/pull/8479))

***Fixed***:

* Bump minimum base package version ([#8443](https://github.com/DataDog/integrations-core/pull/8443))

## 3.1.1 / 2021-01-25 / Agent 7.26.0

***Fixed***:

* Make more explicit which connection was established ([#8416](https://github.com/DataDog/integrations-core/pull/8416))
* Correct default template usage ([#8233](https://github.com/DataDog/integrations-core/pull/8233))

## 3.1.0 / 2020-11-25 / Agent 7.25.0

***Added***:

* Cache the client connection when there are no errors ([#8083](https://github.com/DataDog/integrations-core/pull/8083))

***Fixed***:

* Add config spec ([#7988](https://github.com/DataDog/integrations-core/pull/7988))

## 3.0.0 / 2020-10-31 / Agent 7.24.0

***Changed***:

* QueryManager - Prevent queries leaking between check instances ([#7750](https://github.com/DataDog/integrations-core/pull/7750))

## 2.1.1 / 2020-09-21 / Agent 7.23.0

***Fixed***:

* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))
* Bump jaydebeapi and jpype1 ([#6963](https://github.com/DataDog/integrations-core/pull/6963))

## 2.1.0 / 2020-05-17 / Agent 7.20.0

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

## 2.0.1 / 2020-04-04 / Agent 7.19.0

***Fixed***:

* Lazy import of JDBC libraries ([#6118](https://github.com/DataDog/integrations-core/pull/6118))

## 2.0.0 / 2020-02-22 / Agent 7.18.0

***Changed***:

* Migrate to QueryManager ([#5529](https://github.com/DataDog/integrations-core/pull/5529))

## 1.12.0 / 2020-02-04

***Added***:

* Add ability to only collect data defined in `custom_queries` ([#5217](https://github.com/DataDog/integrations-core/pull/5217)) Thanks [nowhammies](https://github.com/nowhammies).

## 1.11.0 / 2020-01-13 / Agent 7.17.0

***Added***:

* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

***Fixed***:

* Fix deprecated exception ([#5182](https://github.com/DataDog/integrations-core/pull/5182))

## 1.10.1 / 2019-10-07 / Agent 6.15.0

***Fixed***:

* Use fetchall instead of iterating cursor for custom queries. This fixes an issue with the JDBC driver ([#4664](https://github.com/DataDog/integrations-core/pull/4664))

## 1.10.0 / 2019-08-24 / Agent 6.14.0

***Added***:

* Upgrade JPype1 to 0.7.0 ([#4211](https://github.com/DataDog/integrations-core/pull/4211))

## 1.9.0 / 2019-07-08 / Agent 6.13.0

***Added***:

* Upgrade dependencies for Python 3.7 binary wheels ([#4030](https://github.com/DataDog/integrations-core/pull/4030))

## 1.8.0 / 2019-06-01 / Agent 6.12.0

***Added***:

* Support multiple results in custom queries ([#3765](https://github.com/DataDog/integrations-core/pull/3765))

## 1.7.0 / 2019-05-14

***Added***:

* Turn an info log into debug ([#3661](https://github.com/DataDog/integrations-core/pull/3661))
* Adhere to code style ([#3552](https://github.com/DataDog/integrations-core/pull/3552))

## 1.6.0 / 2019-03-29 / Agent 6.11.0

***Added***:

* Add custom_queries config globally ([#3231](https://github.com/DataDog/integrations-core/pull/3231))

## 1.5.0 / 2019-02-18 / Agent 6.10.0

***Added***:

* Support Python 3 ([#3037](https://github.com/DataDog/integrations-core/pull/3037))

***Fixed***:

* Fix tablespace metrics ([#2841](https://github.com/DataDog/integrations-core/pull/2841))

## 1.4.0 / 2018-09-04 / Agent 6.5.0

***Added***:

* Add process metrics ([#1856](https://github.com/DataDog/integrations-core/pull/1856))

***Fixed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))

## 1.3.0 / 2018-06-07

***Added***:

* Support custom queries ([#1528](https://github.com/DataDog/integrations-core/pull/1528))
* Add ability to use the JDBC Driver instead of cx_Oracle ([#1459](https://github.com/DataDog/integrations-core/pull/1459))
* ability to use the JDBC Driver instead of `cx_Oracle` to connect to the database ([#1459](https://github)com/DataDog/integrations-core/issues/1459)

## 1.2.0 / 2018-05-11

***Added***:

* adds metric `oracle.tablespace.offline` ([#1402](https://github)com/DataDog/integrations-core/issues/1402)

***Fixed***:

* fix for DB with offline tablespace. See #1402

## 1.1.0 / 2018-05-11

***Added***:

* adds custom tag support to service checks.

## 1.0.1 / 2018-05-11

### Notes

The metric `oracle.gc_cr_receive_time` has been renamed to `oracle.gc_cr_block_received`
to address an erroneous metric name. Please update your dashboards and monitors.

***Fixed***:

* fix metric name to: `gc_cr_block_received`. See #1179

## 1.0.0 / 2017-10-10

***Added***:

* adds oracle integration ([#680](https://github.com/DataDog/integrations-core/issues/680))

***Fixed***:

* adds oracle integration ([#690](https://github.com/DataDog/integrations-core/issues/690)) (Thanks [@dwjvaughan](https://github.com/dwjvaughan))
