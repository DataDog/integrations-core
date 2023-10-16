# CHANGELOG - datadog_checks_base

## Unreleased

***Fixed***:

* Bump the `pyodbc` version to 4.0.39 ([#16021](https://github.com/DataDog/integrations-core/pull/16021))

## 34.0.0 / 2023-09-29

***Changed***:

* Upgrade to openstacksdk version 1.5.0 ([#15919](https://github.com/DataDog/integrations-core/pull/15919))

***Added***:

* Upgrade clickhouse-driver to 0.2.6 on Python 3 ([#15726](https://github.com/DataDog/integrations-core/pull/15726))
* Upgrade lz4 to 4.3.2 on Python 3 ([#15746](https://github.com/DataDog/integrations-core/pull/15746))
* Update dependencies ([#15922](https://github.com/DataDog/integrations-core/pull/15922))

***Fixed***:

* Fix type `bytes` is not JSON serializable for dbm events ([#15763](https://github.com/DataDog/integrations-core/pull/15763))

## 33.1.0 / 2023-08-25

***Security***:

* Update security dependencies ([#15667](https://github.com/DataDog/integrations-core/pull/15667))
  * in-toto: 2.0.0
  * securesystemslib: 0.28.0

## 33.0.1 / 2023-08-24

***Fixed***:

* Use `DD_TRACE_ENABLED` to disable ddtrace on Windows when using `process_isolation` ([#15635](https://github.com/DataDog/integrations-core/pull/15635))

## 33.0.0 / 2023-08-18

***Changed***:

* Remove python 2 references from SQL Server integration ([#15606](https://github.com/DataDog/integrations-core/pull/15606))

***Added***:

* Dependency update for 7.48 ([#15585](https://github.com/DataDog/integrations-core/pull/15585))
* Improve documentation of APIs ([#15582](https://github.com/DataDog/integrations-core/pull/15582))

***Added***:

* Support Auth through Azure AD MI / Service Principal ([#15591](https://github.com/DataDog/integrations-core/pull/15591))

***Fixed***:

* Downgrade pydantic to 2.0.2 ([#15596](https://github.com/DataDog/integrations-core/pull/15596))
* Bump cryptography to 41.0.3 ([#15517](https://github.com/DataDog/integrations-core/pull/15517))
* Prevent `command already in progress` errors in the Postgres integration ([#15489](https://github.com/DataDog/integrations-core/pull/15489))
* Disable ddtrace when using process_isolation on Windows ([#15622](https://github.com/DataDog/integrations-core/pull/15622))

## 32.7.0 / 2023-08-10

***Added***:

* Bump psycopg3 version && add timeouts on blocking functions ([#15492](https://github.com/DataDog/integrations-core/pull/15492))
* Add support for implementing diagnostics for `agent diagnose` ([#14394](https://github.com/DataDog/integrations-core/pull/14394))

***Fixed***:

* Upgrade postgres check to psycopg3 ([#15411](https://github.com/DataDog/integrations-core/pull/15411))

## 32.6.0 / 2023-07-31

***Added***:

* Upgrade ddtrace to 1.11.2 on Python 3 ([#15144](https://github.com/DataDog/integrations-core/pull/15144))
* Update generated config models ([#15212](https://github.com/DataDog/integrations-core/pull/15212))

***Fixed***:

* Fix types for generated config models ([#15334](https://github.com/DataDog/integrations-core/pull/15334))
* Upgrade pydantic ([#15394](https://github.com/DataDog/integrations-core/pull/15394))
* Revert "Bump pydantic version in the agent_requirements.in file (#153… ([#15338](https://github.com/DataDog/integrations-core/pull/15338))
* Bump pydantic version in the agent_requirements.in file ([#15320](https://github.com/DataDog/integrations-core/pull/15320))

## 32.5.1 / 2023-07-19

***Fixed***:

* Revert to requesting Prometheus format by default ([#15292](https://github.com/DataDog/integrations-core/pull/15292))

## 32.5.0 / 2023-07-10

***Added***:

* Bump dependencies for Agent 7.47 ([#15145](https://github.com/DataDog/integrations-core/pull/15145))
* Upgrade ddtrace to 1.11.2 on Python 3 ([#14367](https://github.com/DataDog/integrations-core/pull/14367))

***Fixed***:

* Revert "Upgrade ddtrace to 1.11.2 on Python 3 (#14367)" ([#15143](https://github.com/DataDog/integrations-core/pull/15143))
* Bump the confluent-kafka version ([#14665](https://github.com/DataDog/integrations-core/pull/14665))
* Allow non-443 port to be used in intermediate certs ([#14817](https://github.com/DataDog/integrations-core/pull/14817))

## 32.4.0 / 2023-06-23

***Added***:

* Internally compile the `include` patterns in the autodiscovery feature ([#14768](https://github.com/DataDog/integrations-core/pull/14768))
* Make cancel() synchronous in DBMAsyncJob ([#14717](https://github.com/DataDog/integrations-core/pull/14717))

***Fixed***:

* Move cancel waiting logic to test functions for DBMAsyncJob  ([#14773](https://github.com/DataDog/integrations-core/pull/14773))
* Update requests-toolbelt version ([#14748](https://github.com/DataDog/integrations-core/pull/14748))
* Update requests library ([#14670](https://github.com/DataDog/integrations-core/pull/14670))
* Bump snowflake connector python to 3.0.4 ([#14675](https://github.com/DataDog/integrations-core/pull/14675))
* Bump Python version from py3.8 to py3.9 ([#14701](https://github.com/DataDog/integrations-core/pull/14701))

## 32.3.1 / 2023-06-02 / Agent 7.46.0

***Fixed***:

* Downgrade an info log to debug ([#14667](https://github.com/DataDog/integrations-core/pull/14667))

## 32.3.0 / 2023-05-26

***Added***:

* Support ingesting pg_settings for `dbm` users ([#14577](https://github.com/DataDog/integrations-core/pull/14577))

***Fixed***:

* Revert protobuf dependency update ([#14618](https://github.com/DataDog/integrations-core/pull/14618))
* Update dependencies ([#14594](https://github.com/DataDog/integrations-core/pull/14594))
* Fix kubelet check failing to initialize when get_connection_info is empty ([#14546](https://github.com/DataDog/integrations-core/pull/14546))

## 32.2.0 / 2023-05-05

***Added***:

* Add an ignore_connection_errors option to the openmetrics check ([#14504](https://github.com/DataDog/integrations-core/pull/14504))

## 32.1.0 / 2023-05-04

***Added***:

* Create `tag_not_null` type which doesn't set the tag when tag value is none ([#14503](https://github.com/DataDog/integrations-core/pull/14503))

***Fixed***:

* Fix bug on empty openmetrics scrape response ([#14508](https://github.com/DataDog/integrations-core/pull/14508))

## 32.0.0 / 2023-04-25

***Changed***:

* Implement automatic exposition format detection ([#14445](https://github.com/DataDog/integrations-core/pull/14445))

## 31.0.2 / 2023-05-31 / Agent 7.45.0

***Fixed***:

* Backport pydantic 1.10.8 upgrade to 7.45 ([#14655](https://github.com/DataDog/integrations-core/pull/14655))

## 31.0.1 / 2023-04-19

***Fixed***:

* Do not add `freezegun` dependency to agent ([#14393](https://github.com/DataDog/integrations-core/pull/14393))

## 31.0.0 / 2023-04-14

***Changed***:

* Replace `kafka-python` dependency with `confluent-kafka-python` ([#13918](https://github.com/DataDog/integrations-core/pull/13918))

***Added***:

* Update dependencies ([#14357](https://github.com/DataDog/integrations-core/pull/14357))
* Update redis to 4.5.4 ([#14270](https://github.com/DataDog/integrations-core/pull/14270))

***Fixed***:

* Fix duplicate events bug ([#14020](https://github.com/DataDog/integrations-core/pull/14020))

## 30.2.0 / 2023-03-07 / Agent 7.44.0

***Added***:

* Upgrade openstacksdk dependency ([#14109](https://github.com/DataDog/integrations-core/pull/14109))

## 30.1.0 / 2023-03-03

***Added***:

* Update kubernetes and supervisor dependencies ([#14093](https://github.com/DataDog/integrations-core/pull/14093))

***Fixed***:

* Do not install gssapi and dtrace on py2 on arm macs ([#13749](https://github.com/DataDog/integrations-core/pull/13749))
* Remove the use of the deprecated `pkg_resources` package ([#13842](https://github.com/DataDog/integrations-core/pull/13842))

# 30.0.2 / 2023-03-02

***Fixed***:

* Bump dependency `snowflake-connector-python` to 3.0.1 ([#14073](https://github.com/DataDog/integrations-core/pull/14073))

## 30.0.1 / 2023-02-28 / Agent 7.43.1

***Fixed***:

* Update cryptography to 39.0.1 ([#13913](https://github.com/DataDog/integrations-core/pull/13913))

## 30.0.0 / 2023-01-20 / Agent 7.43.0

***Changed***:

* Skip typo for not yet installed Windows performance counters to allow collection of subsequent counters ([#13678](https://github.com/DataDog/integrations-core/pull/13678))

***Added***:

* Bump snowflake to 2.8.3 ([#13756](https://github.com/DataDog/integrations-core/pull/13756))

***Fixed***:

* Update dependencies ([#13726](https://github.com/DataDog/integrations-core/pull/13726))

## 29.0.0 / 2023-01-10

***Removed***:

* Update TUF to 2.0.0 ([#13331](https://github.com/DataDog/integrations-core/pull/13331))

***Changed***:

* Improve integration tracing of warnings & errors ([#13620](https://github.com/DataDog/integrations-core/pull/13620))

***Added***:

* Autodiscovery in Agent Integrations ([#13656](https://github.com/DataDog/integrations-core/pull/13656))
* Inject trace context into logs when integration_tracing is enabled ([#13636](https://github.com/DataDog/integrations-core/pull/13636))
* Update integration tracing naming scheme ([#13579](https://github.com/DataDog/integrations-core/pull/13579))
* Add option to enable profiling of Python integrations ([#13576](https://github.com/DataDog/integrations-core/pull/13576))
* Add Cloudera integration ([#13244](https://github.com/DataDog/integrations-core/pull/13244))

## 28.0.2 / 2023-01-27 / Agent 7.42.1

***Fixed***:

* Backport snowflake-connector-python bump 2.8.3 to 7.42.x ([#13794](https://github.com/DataDog/integrations-core/pull/13794))

## 28.0.1 / 2022-12-16 / Agent 7.42.0

***Fixed***:

* Fixed incorrect counter type determination and error reporting on the first collection ([#13489](https://github.com/DataDog/integrations-core/pull/13489))

## 28.0.0 / 2022-12-09

***Changed***:

* Update Oracle check to use python-oracledb library ([#13298](https://github.com/DataDog/integrations-core/pull/13298))

***Fixed***:

* Update dependencies ([#13478](https://github.com/DataDog/integrations-core/pull/13478))

## 27.5.0 / 2022-12-06

***Added***:

* Implement multi-instance counters without Windows PdhEnumObjects API ([#13243](https://github.com/DataDog/integrations-core/pull/13243))

***Fixed***:

* Do not install psycopg2-binary on arm macs ([#13343](https://github.com/DataDog/integrations-core/pull/13343))
* Update Snowflake connector and cryptography dependencies ([#13367](https://github.com/DataDog/integrations-core/pull/13367))
* Remove `default_backend` parameter from cryptography calls ([#13333](https://github.com/DataDog/integrations-core/pull/13333))
* Update protobuf ([#13262](https://github.com/DataDog/integrations-core/pull/13262))

## 27.4.2 / 2022-10-28 / Agent 7.41.0

## 27.4.1 / 2022-10-12

***Fixed***:

* Update dependencies ([#13205](https://github.com/DataDog/integrations-core/pull/13205) and [#13207](https://github.com/DataDog/integrations-core/pull/13207))
* Make OpenMetrics checks honor `empty_default_hostname` option ([#13146](https://github.com/DataDog/integrations-core/pull/13146))
* Prevent fork bomb when defining the experimental `process_isolation` option globally in the `init_config` section ([#13091](https://github.com/DataDog/integrations-core/pull/13091))

## 27.4.0 / 2022-10-11

***Added***:

* Add utility to handle concurrent evaluation of conditions ([#13053](https://github.com/DataDog/integrations-core/pull/13053))

## 27.3.1 / 2022-10-12 / Agent 7.40.0

***Fixed***:

* Prevent fork bomb when defining the experimental process_isolation option globally in the init_config section ([#13094](https://github.com/DataDog/integrations-core/pull/13094))

## 27.3.0 / 2022-09-22

***Added***:

* Add ability for checks to run in an ephemeral process at every run ([#12986](https://github.com/DataDog/integrations-core/pull/12986))

## 27.2.0 / 2022-09-19

***Added***:

* Add agent config option to control Window Counter refresh rate ([#12665](https://github.com/DataDog/integrations-core/pull/12665))

***Fixed***:

* Bump dependencies for 7.40 ([#12896](https://github.com/DataDog/integrations-core/pull/12896))

## 27.1.0 / 2022-09-09

***Added***:

* Add OAuth functionality to the HTTP util ([#12884](https://github.com/DataDog/integrations-core/pull/12884))
* Add `packaging` to dependencies ([#12753](https://github.com/DataDog/integrations-core/pull/12753))

***Fixed***:

* Fix formatting of message ([#12827](https://github.com/DataDog/integrations-core/pull/12827))

## 27.0.0 / 2022-08-05 / Agent 7.39.0

***Changed***:

* Upgrade pymongo to 4.2 ([#12594](https://github.com/DataDog/integrations-core/pull/12594))

***Security***:

* Bump `lxml` package ([#12663](https://github.com/DataDog/integrations-core/pull/12663))

***Fixed***:

* Dependency updates ([#12653](https://github.com/DataDog/integrations-core/pull/12653))
* Pin `pymysql` to `0.10.1` ([#12612](https://github.com/DataDog/integrations-core/pull/12612))
* Better failed assertion message, print return code ([#12615](https://github.com/DataDog/integrations-core/pull/12615))

## 26.0.0 / 2022-07-22

***Removed***:

* Remove inventories configuration submission ([#12500](https://github.com/DataDog/integrations-core/pull/12500))

***Added***:

* Support custom messages in `QueryManager` queries of type `'service_check'` ([#12537](https://github.com/DataDog/integrations-core/pull/12537))

## 25.6.0 / 2022-07-11

***Added***:

* Ship `pymongo-srv` to support DNS seed connection schemas ([#12442](https://github.com/DataDog/integrations-core/pull/12442))

***Fixed***:

* Fix typo detection for config field aliases ([#12468](https://github.com/DataDog/integrations-core/pull/12468))
* [PerfCountersBaseCheck] Refresh performance objects in a separate thread ([#12372](https://github.com/DataDog/integrations-core/pull/12372))
* Allow empty username and password for basic auth ([#12437](https://github.com/DataDog/integrations-core/pull/12437))

## 25.5.1 / 2022-08-08 / Agent 7.38.2

***Security***:

* Bump `lxml` package ([#12663](https://github.com/DataDog/integrations-core/pull/12663))

## 25.5.0 / 2022-07-08 / Agent 7.38.0

***Security***:

* Upgrade pyjwt to 2.4.0 ([#12481](https://github.com/DataDog/integrations-core/pull/12481))

## 25.4.2 / 2022-06-27

***Fixed***:

* Change refreshing counters log level to debug ([#12069](https://github.com/DataDog/integrations-core/pull/12069))

## 25.4.1 / 2022-05-15 / Agent 7.37.0

***Fixed***:

* Upgrade dependencies ([#11958](https://github.com/DataDog/integrations-core/pull/11958))

## 25.4.0 / 2022-05-10

***Added***:

* Support dynamic bearer tokens (Bound Service Account Token Volume) ([#11915](https://github.com/DataDog/integrations-core/pull/11915))
* Refactor the QueryManager to support multiple instances in checks ([#11869](https://github.com/DataDog/integrations-core/pull/11869))

***Fixed***:

* Fix incorrect OpenMetrics V2 check exposition format HTTP header ([#11899](https://github.com/DataDog/integrations-core/pull/11899)) Thanks [jalaziz](https://github.com/jalaziz).
* Allow tags that are just a value with no key ([#11973](https://github.com/DataDog/integrations-core/pull/11973))
* Add the ability to exclude endpoint tag ([#11956](https://github.com/DataDog/integrations-core/pull/11956))
* Don't pin urllib3 ([#11944](https://github.com/DataDog/integrations-core/pull/11944))

## 25.3.1 / 2022-05-05 / Agent 7.36.0

***Fixed***:

* Fallback Kubernetes client version to 22.6 to avoid failures on non-standard POD conditions ([#11928](https://github.com/DataDog/integrations-core/pull/11928))

## 25.3.0 / 2022-04-28

***Added***:

* Upgrade `orjson` dependency ([#11843](https://github.com/DataDog/integrations-core/pull/11843))

## 25.2.2 / 2022-04-12

***Fixed***:

* Fix obfuscate_sql_with_metadata wrapper memory usage ([#11815](https://github.com/DataDog/integrations-core/pull/11815))

## 25.2.1 / 2022-04-11

***Fixed***:

* Fix `metric_patterns` option to support namespaces ([#11795](https://github.com/DataDog/integrations-core/pull/11795))

## 25.2.0 / 2022-04-05

***Added***:

* Add integration_tracing option ([#11761](https://github.com/DataDog/integrations-core/pull/11761))
* Add gssapi as a dependency ([#11725](https://github.com/DataDog/integrations-core/pull/11725))
* Upgrade dependencies ([#11726](https://github.com/DataDog/integrations-core/pull/11726))

***Fixed***:

* Support newer versions of `click` ([#11746](https://github.com/DataDog/integrations-core/pull/11746))

## 25.1.0 / 2022-03-16

***Added***:

* Add `metric_patterns` options to filter all metric submission by a list of regexes ([#11508](https://github.com/DataDog/integrations-core/pull/11508))
* Upgrade `requests` dependency ([#11603](https://github.com/DataDog/integrations-core/pull/11603))

## 25.0.1 / 2022-02-24 / Agent 7.35.0

***Fixed***:

* Properly raise scraper error in OpenMetrics v2 ([#11564](https://github.com/DataDog/integrations-core/pull/11564))

## 25.0.0 / 2022-02-19

***Changed***:

* *BREAKING CHANGE* Remove pyhdb ([#11469](https://github.com/DataDog/integrations-core/pull/11469))

***Added***:

* Add `pyproject.toml` file ([#11301](https://github.com/DataDog/integrations-core/pull/11301))
* Detect and warn on potential typos in configuration options ([#11211](https://github.com/DataDog/integrations-core/pull/11211))

***Fixed***:

* Add more error handling when detecting typos ([#11519](https://github.com/DataDog/integrations-core/pull/11519))
* Fix edge case in tracing utils ([#11516](https://github.com/DataDog/integrations-core/pull/11516))
* Properly create list of known options when detecting typos ([#11482](https://github.com/DataDog/integrations-core/pull/11482))
* Fail gracefully when scraping OpenMetrics endpoints ([#11281](https://github.com/DataDog/integrations-core/pull/11281))
* Update error message when unable to connect to any possible prometheus urls ([#11197](https://github.com/DataDog/integrations-core/pull/11197))
* Update obfuscator wrapper to return empty string ([#11277](https://github.com/DataDog/integrations-core/pull/11277))

## 24.0.0 / 2022-02-02

***Changed***:

* Add tls_protocols_allowed configuration option ([#11237](https://github.com/DataDog/integrations-core/pull/11237))

***Added***:

* Upgrade psutil to 5.9.0 ([#11139](https://github.com/DataDog/integrations-core/pull/11139))

## 23.7.7 / 2022-04-12

***Fixed***:

* Fix obfuscate_sql_with_metadata wrapper memory usage ([#11815](https://github.com/DataDog/integrations-core/pull/11815))

## 23.7.6 / 2022-02-03 / Agent 7.34.0

***Fixed***:

* Update obfuscator wrapper to return empty string ([#11277](https://github.com/DataDog/integrations-core/pull/11277))

## 23.7.5 / 2022-02-01

***Fixed***:

* Bump redis dependency to 4.0.2 ([#11247](https://github.com/DataDog/integrations-core/pull/11247))

## 23.7.4 / 2022-01-18

***Fixed***:

* Raise CheckException in case of connectivity issue for OpenMetrics-based checks ([#11153](https://github.com/DataDog/integrations-core/pull/11153))

## 23.7.3 / 2022-01-12

***Fixed***:

* Fix obfuscate_sql_with_metadata query being None ([#11094](https://github.com/DataDog/integrations-core/pull/11094))

## 23.7.2 / 2022-01-08 / Agent 7.33.0

***Fixed***:

* Add urllib3 as dependency ([#11069](https://github.com/DataDog/integrations-core/pull/11069))

## 23.7.1 / 2022-01-07

***Fixed***:

* Fix tracing_method using self argument ([#11042](https://github.com/DataDog/integrations-core/pull/11042))
* Fix obfuscate_sql_with_metadata wrapper not handling json.loads() edge case ([#11038](https://github.com/DataDog/integrations-core/pull/11038))

## 23.7.0 / 2022-01-04

***Added***:

* Add obfuscate_sql_with_metadata wrapper and update stub ([#10878](https://github.com/DataDog/integrations-core/pull/10878))
* Add new `tls_only` choice to the `bearer_token` parameter that sends the bearer token only to secure HTTPS endpoints ([#10706](https://github.com/DataDog/integrations-core/pull/10706))
* Add Windows support to IBM MQ ([#10737](https://github.com/DataDog/integrations-core/pull/10737))
* Add debug metrics for metric context limits ([#10808](https://github.com/DataDog/integrations-core/pull/10808))
* Support custom transformer ([#10753](https://github.com/DataDog/integrations-core/pull/10753))

***Fixed***:

* Don't add autogenerated comments to deprecation files ([#11014](https://github.com/DataDog/integrations-core/pull/11014))
* Vendor flup client FCGIApp ([#10953](https://github.com/DataDog/integrations-core/pull/10953))
* Fix obfuscate_sql wrapper None value ([#11016](https://github.com/DataDog/integrations-core/pull/11016))
* Add comment to autogenerated model files ([#10945](https://github.com/DataDog/integrations-core/pull/10945))
* Fix incorrect logging in case of exceptions thrown during job cancellation ([#10934](https://github.com/DataDog/integrations-core/pull/10934))

## 23.6.0 / 2021-12-20

***Security***:

* Bump lxml package ([#10904](https://github.com/DataDog/integrations-core/pull/10904))

## 23.5.0 / 2021-12-08

***Added***:

* Add decorator for tracking execution statistics of check methods ([#10809](https://github.com/DataDog/integrations-core/pull/10809))
* Add detailed trace to all integrations ([#10679](https://github.com/DataDog/integrations-core/pull/10679))

***Fixed***:

* Import ddtrace only when needed ([#10800](https://github.com/DataDog/integrations-core/pull/10800))

## 23.4.0 / 2021-11-30

***Added***:

* [OpenMetricsV2] Support custom transformers by regex matching metric names ([#10753](https://github.com/DataDog/integrations-core/pull/10753))

***Fixed***:

* Bump cachetools ([#10742](https://github.com/DataDog/integrations-core/pull/10742))
* Bump redis dependency ([#9383](https://github.com/DataDog/integrations-core/pull/9383))

## 23.3.3 / 2021-12-16

***Fixed***:

* Ensure TLSContextWrapper creates TLS context with the proper values ([#10875](https://github.com/DataDog/integrations-core/pull/10875))

## 23.3.2 / 2021-11-23

***Fixed***:

* [PerfCountersBaseCheck] Improve logging when expected counters are not found ([#10701](https://github.com/DataDog/integrations-core/pull/10701))
* [PerfCountersBaseCheck] Fix default machine connection ([#10698](https://github.com/DataDog/integrations-core/pull/10698))

## 23.3.1 / 2021-11-19

***Fixed***:

* fix `mmh3.hash64` unicode exception with python2 ([#10685](https://github.com/DataDog/integrations-core/pull/10685))

## 23.3.0 / 2021-11-12

***Added***:

* Add new base class for monitoring Windows performance counters ([#10504](https://github.com/DataDog/integrations-core/pull/10504))
* Update dependencies ([#10580](https://github.com/DataDog/integrations-core/pull/10580))

## 23.2.0 / 2021-11-10

***Added***:

* Add option to collect OpenMetrics counters on first scrape ([#10589](https://github.com/DataDog/integrations-core/pull/10589))
* Add support for OpenMetrics include_labels option ([#10493](https://github.com/DataDog/integrations-core/pull/10493))
* Upgrade psycopg2 on Python 3 ([#10442](https://github.com/DataDog/integrations-core/pull/10442))
* Add more utilities ([#10448](https://github.com/DataDog/integrations-core/pull/10448))
* Add support for other logical operators for multiple conditions of the same property ([#10138](https://github.com/DataDog/integrations-core/pull/10138))

***Fixed***:

* Fix unintentional limit on dbm instances from ThreadPoolExecutor's default max_workers ([#10460](https://github.com/DataDog/integrations-core/pull/10460))
* Revert "Upgrade psycopg2 on Python 3" ([#10456](https://github.com/DataDog/integrations-core/pull/10456))
* Update tuf to 0.19.0 for python 3 ([#10444](https://github.com/DataDog/integrations-core/pull/10444))
* [OpenMetricsV2] Allow empty namespaces ([#10420](https://github.com/DataDog/integrations-core/pull/10420))
* Add warning when no query is configured ([#10336](https://github.com/DataDog/integrations-core/pull/10336))

## 23.1.5 / 2021-10-22 / Agent 7.32.0

***Fixed***:

* Fix unintentional limit on dbm instances from ThreadPoolExecutor's default max_workers ([#10460](https://github.com/DataDog/integrations-core/pull/10460))

## 23.1.4 / 2021-10-19

***Fixed***:

* Update tuf to 0.19.0 for Python 3 ([#10444](https://github.com/DataDog/integrations-core/pull/10444))

## 23.1.3 / 2021-10-15

***Fixed***:

* [OpenMetricsV2] Allow empty namespaces ([#10420](https://github.com/DataDog/integrations-core/pull/10420))
* Add warning when no query is configured ([#10336](https://github.com/DataDog/integrations-core/pull/10336))

## 23.1.2 / 2021-10-05

***Fixed***:

* Remove `server` from the list of generic tags ([#10344](https://github.com/DataDog/integrations-core/pull/10344))

## 23.1.1 / 2021-10-05

***Fixed***:

* Add warning when no query is configured ([#10336](https://github.com/DataDog/integrations-core/pull/10336))

## 23.1.0 / 2021-10-01

***Added***:

* Add only_custom_queries option to database utils ([#10314](https://github.com/DataDog/integrations-core/pull/10314))
* Update dependencies ([#10258](https://github.com/DataDog/integrations-core/pull/10258))

## 23.0.0 / 2021-09-29

***Changed***:

* DBMAsyncJob send internal metrics as raw ([#10274](https://github.com/DataDog/integrations-core/pull/10274))

***Added***:

* Update dependencies ([#10228](https://github)com/DataDog/integrations-core/pull/10228)
* Add HTTP option to control the size of streaming responses ([#10183](https://github.com/DataDog/integrations-core/pull/10183))
* Add new function to report dbm-activity events ([#10223](https://github.com/DataDog/integrations-core/pull/10223))

## 22.0.0 / 2021-09-24

***Removed***:

* Drop snowflake support from py2, bump requests ([#10105](https://github.com/DataDog/integrations-core/pull/10105))

***Added***:

* Upgrade python-dateutil to 2.8.2 ([#10206](https://github.com/DataDog/integrations-core/pull/10206))
* Add allow_redirect option ([#10160](https://github.com/DataDog/integrations-core/pull/10160))

## 21.3.0 / 2021-09-21

***Added***:

* Add force yaml loader utils ([#10163](https://github.com/DataDog/integrations-core/pull/10163))

## 21.2.1 / 2021-09-20

***Fixed***:

* Add limit to tag split ([#10165](https://github.com/DataDog/integrations-core/pull/10165))
* Revert "Allow non-default yaml loader and dumper (#10032)" ([#10154](https://github.com/DataDog/integrations-core/pull/10154))
* Fix mypy tests ([#10134](https://github.com/DataDog/integrations-core/pull/10134))
* Add server as generic tag ([#10100](https://github.com/DataDog/integrations-core/pull/10100))
* Fix TLSContextWrapper to not override tls_verify ([#10098](https://github.com/DataDog/integrations-core/pull/10098))

## 21.2.0 / 2021-09-10

***Added***:

* Disable generic tags ([#10027](https://github.com/DataDog/integrations-core/pull/10027))

## 21.1.0 / 2021-09-07

***Added***:

* Add dependency `foundationdb` version `6.3.18` ([#10050](https://github.com/DataDog/integrations-core/pull/10050))

***Fixed***:

* Bump snowflake and requests for Py3 ([#10060](https://github.com/DataDog/integrations-core/pull/10060))
* Allow non-default yaml loader and dumper ([#10032](https://github.com/DataDog/integrations-core/pull/10032))
* Set disable_unsafe_yaml default value ([#10026](https://github.com/DataDog/integrations-core/pull/10026))

## 21.0.1 / 2021-08-23 / Agent 7.31.0

***Fixed***:

* Revert "Raise exception during tests for OK service checks sent with messages" ([#9936](https://github.com/DataDog/integrations-core/pull/9936))

## 21.0.0 / 2021-08-22

***Changed***:

* Remove messages for integrations for OK service checks ([#9888](https://github.com/DataDog/integrations-core/pull/9888))

***Added***:

* Raise exception during tests for OK service checks sent with messages ([#9898](https://github.com/DataDog/integrations-core/pull/9898))
* Add `kubernetes_state.statefulset.count` metric ([#9813](https://github.com/DataDog/integrations-core/pull/9813))
* Bump openstacksdk and add missing metrics ([#9861](https://github.com/DataDog/integrations-core/pull/9861))
* Extend `QueryManager` query type ([#9874](https://github.com/DataDog/integrations-core/pull/9874))
* [OpenMetricsV2] Improve label sharing behavior ([#9804](https://github.com/DataDog/integrations-core/pull/9804))
* Disable generic tags ([#9791](https://github.com/DataDog/integrations-core/pull/9791))

***Fixed***:

* Revert requests bump back to 2.22.0 ([#9912](https://github.com/DataDog/integrations-core/pull/9912))
* Send the correct hostname with metrics when DBM is enabled ([#9865](https://github.com/DataDog/integrations-core/pull/9865))
* Fix database checks' failure caused by a hostname that is too long ([#9778](https://github.com/DataDog/integrations-core/pull/9778)) Thanks [ichizero](https://github.com/ichizero).
* Check monotonic type when asserting histograms ([#9825](https://github.com/DataDog/integrations-core/pull/9825))

## 20.2.0 / 2021-07-12 / Agent 7.30.0

***Added***:

* Upgrade downloader after ceremony ([#9556](https://github.com/DataDog/integrations-core/pull/9556))

## 20.1.0 / 2021-07-08

***Added***:

* Add `db.utils.DBMAsyncJob` ([#9656](https://github.com/DataDog/integrations-core/pull/9656))
* Add a `possible_prometheus_urls` parameter to the OpenMetrics base check ([#9573](https://github.com/DataDog/integrations-core/pull/9573))
* Upgrade some core dependencies ([#9499](https://github.com/DataDog/integrations-core/pull/9499))

## 20.0.1 / 2021-06-24

***Fixed***:

* Fix Python 2 integer division bug in db.util `ConstantRateLimiter` ([#9592](https://github.com/DataDog/integrations-core/pull/9592))

## 20.0.0 / 2021-06-22

***Changed***:

* Remove monotonic count from ignored types in no duplicate assertion ([#9463](https://github.com/DataDog/integrations-core/pull/9463))
* Upgrade psycopg2-binary to 2.8.6 ([#9535](https://github.com/DataDog/integrations-core/pull/9535))

***Added***:

* Add `RateLimitingTTLCache` to `db.utils` ([#9582](https://github.com/DataDog/integrations-core/pull/9582))
* Bump pymongo to 3.8 ([#9557](https://github.com/DataDog/integrations-core/pull/9557))
* Upgrade `aerospike` dependency on Python 3 ([#9552](https://github.com/DataDog/integrations-core/pull/9552))

***Fixed***:

* Upgrade pydantic to 1.8.2 ([#9533](https://github.com/DataDog/integrations-core/pull/9533))

## 19.0.0 / 2021-05-28 / Agent 7.29.0

***Removed***:

* Remove unused `utils.db.statement_samples` client ([#9166](https://github.com/DataDog/integrations-core/pull/9166))
* Remove unused apply_row_limits in statement_metrics.py ([#9378](https://github.com/DataDog/integrations-core/pull/9378))

***Changed***:

* Add flush first value to Openmetrics histogram buckets ([#9276](https://github.com/DataDog/integrations-core/pull/9276))
* Change 'collision in cached query metrics' log from debug to error ([#9268](https://github.com/DataDog/integrations-core/pull/9268))

***Added***:

* Remove unused dependency ([#9435](https://github.com/DataDog/integrations-core/pull/9435))
* Support "ignore_tags" configuration ([#9392](https://github.com/DataDog/integrations-core/pull/9392))
* Upgrade ClickHouse dependencies ([#9344](https://github.com/DataDog/integrations-core/pull/9344))
* [OpenMetricsV2] Add an option to send sum and count information when using distribution metrics ([#9301](https://github.com/DataDog/integrations-core/pull/9301))
* Improve performance of using extra tags when executing a QueryManager ([#8466](https://github.com/DataDog/integrations-core/pull/8466))
* Add `hostname` parameter to QueryManager ([#9260](https://github.com/DataDog/integrations-core/pull/9260))

***Fixed***:

* Fix AttributeError in AIA chasing ([#9328](https://github.com/DataDog/integrations-core/pull/9328))
* Upgrade pyvmomi to 7.0.2 ([#9287](https://github.com/DataDog/integrations-core/pull/9287))

## 18.3.0 / 2021-04-27

***Added***:

* Add merging of duplicate rows in statement_metrics ([#9227](https://github.com/DataDog/integrations-core/pull/9227))
* Upgrade `python-binary-memcached` dependency ([#9251](https://github.com/DataDog/integrations-core/pull/9251))

## 18.2.0 / 2021-04-19 / Agent 7.28.0

***Added***:

* Allow the loading of arbitrary configuration models ([#9180](https://github.com/DataDog/integrations-core/pull/9180))

## 18.1.0 / 2021-04-16

***Security***:

* Upgrade lxml python package ([#9173](https://github.com/DataDog/integrations-core/pull/9173))

***Added***:

* Add unix_time format to QueryManager time_elapsed transformer ([#9174](https://github.com/DataDog/integrations-core/pull/9174))
* Support new aggregator APIs for the event platform ([#9165](https://github.com/DataDog/integrations-core/pull/9165))

***Fixed***:

* Upgrade ddtrace ([#9127](https://github.com/DataDog/integrations-core/pull/9127))

## 18.0.0 / 2021-04-07

***Changed***:

* Refactor kubelet and eks_fargate checks to use `KubeletBase` ([#8798](https://github.com/DataDog/integrations-core/pull/8798))

***Added***:

* Add testing module for frequently used `pytest`-related utilities ([#9081](https://github.com/DataDog/integrations-core/pull/9081))
* Add `native_dynamic` OpenMetrics transformer ([#9077](https://github.com/DataDog/integrations-core/pull/9077))

## 17.0.0 / 2021-03-30

***Changed***:

* Add a timeout for Kubernetes API calls ([#9035](https://github.com/DataDog/integrations-core/pull/9035))

***Added***:

* Add `KubeletBase` base class ([#9051](https://github.com/DataDog/integrations-core/pull/9051))
* Upgrade cryptography to 3.4.6 on Python 3 ([#8764](https://github.com/DataDog/integrations-core/pull/8764))
* Make counter refresh-related code more reusable ([#8822](https://github.com/DataDog/integrations-core/pull/8822))

## 16.9.0 / 2021-03-22

***Added***:

* Add config spec data model consumer ([#8675](https://github.com/DataDog/integrations-core/pull/8675))

## 16.8.0 / 2021-03-18

***Added***:

* AIA chasing for HTTP ([#8725](https://github.com/DataDog/integrations-core/pull/8725))
* Upgrade pywin32 on Python 3 ([#8845](https://github.com/DataDog/integrations-core/pull/8845))

## 16.7.0 / 2021-03-16

***Added***:

* Add new precision time function ([#8838](https://github.com/DataDog/integrations-core/pull/8838))

## 16.6.1 / 2021-03-12 / Agent 7.27.0

***Fixed***:

* Import kube client lazily ([#8820](https://github.com/DataDog/integrations-core/pull/8820))

## 16.6.0 / 2021-03-05

***Added***:

* Upgrade PyJWT to 2.0.1 on Python 3 ([#8762](https://github.com/DataDog/integrations-core/pull/8762))

***Fixed***:

* Improve orjson compatibility ([#8767](https://github.com/DataDog/integrations-core/pull/8767))

## 16.5.0 / 2021-03-04

***Security***:

* Upgrade pyyaml python package ([#8707](https://github.com/DataDog/integrations-core/pull/8707))
* Upgrade cryptography python package ([#8611](https://github.com/DataDog/integrations-core/pull/8611))

***Added***:

* Add ability to look for wildcards in Prometheus metric transformers ([#8750](https://github.com/DataDog/integrations-core/pull/8750))
* Add support for Kubernetes leader election based on Lease objects ([#8535](https://github.com/DataDog/integrations-core/pull/8535))
* Collect postgres statement samples & execution plans for deep database monitoring ([#8627](https://github.com/DataDog/integrations-core/pull/8627))
* Add cancel method to the AgentCheck base class, allowing cleanup of resources when checks are unscheduled. ([#8463](https://github.com/DataDog/integrations-core/pull/8463))
* Add logical utility functions ([#8590](https://github.com/DataDog/integrations-core/pull/8590))

***Fixed***:

* Remove unused AgentCheck attribute ([#8619](https://github.com/DataDog/integrations-core/pull/8619))

## 16.4.0 / 2021-02-09

***Added***:

* Upgrade JPype1 to 1.2.1 ([#8479](https://github.com/DataDog/integrations-core/pull/8479))
* Add support for legacy config to OpenMetricsCompatibilityScraper ([#8507](https://github.com/DataDog/integrations-core/pull/8507))

## 16.3.2 / 2021-02-01 / Agent 7.26.0

***Fixed***:

* Fix histogram upper bound label name for new OpenMetrics implementation ([#8505](https://github.com/DataDog/integrations-core/pull/8505))
* Provide error message on subprocess output ([#8455](https://github.com/DataDog/integrations-core/pull/8455))

## 16.3.1 / 2021-01-29

***Fixed***:

* Fix Prometheus summary quantile metrics ([#8488](https://github.com/DataDog/integrations-core/pull/8488))

## 16.3.0 / 2021-01-28

***Security***:

* Upgrade cryptography python package ([#8476](https://github.com/DataDog/integrations-core/pull/8476))

## 16.2.0 / 2021-01-24

***Added***:

* Add `rate` OpenMetrics transformer ([#8434](https://github.com/DataDog/integrations-core/pull/8434))
* Remove any OpenMetrics metric prefixes immediately during parsing ([#8432](https://github.com/DataDog/integrations-core/pull/8432))
* Add OpenMetrics option to share labels conditionally based on sample values ([#8431](https://github.com/DataDog/integrations-core/pull/8431))

***Fixed***:

* Remove class substitution logic for new OpenMetrics base class ([#8435](https://github.com/DataDog/integrations-core/pull/8435))

## 16.1.0 / 2021-01-22

***Added***:

* Add new version of OpenMetrics base class ([#8300](https://github.com/DataDog/integrations-core/pull/8300))

***Fixed***:

* Properly support check namespacing for the `submit_histogram_bucket` method ([#8390](https://github.com/DataDog/integrations-core/pull/8390))

## 16.0.0 / 2021-01-13

***Removed***:

* Remove unneccessary `pytz` dependency ([#8354](https://github.com/DataDog/integrations-core/pull/8354))

***Added***:

* Add `no_op` utility ([#8356](https://github.com/DataDog/integrations-core/pull/8356))
* Support tags set at runtime on the DB QueryManager ([#8304](https://github.com/DataDog/integrations-core/pull/8304))
* Add the `host` tag to RDS instances' parsed tags ([#8292](https://github.com/DataDog/integrations-core/pull/8292))
* Update prometheus mixin to use the request wrapper ([#8223](https://github.com/DataDog/integrations-core/pull/8223))
* Add optional argument for overriding get_tls_context() parameters ([#8275](https://github.com/DataDog/integrations-core/pull/8275))
* Allow semver version metadata to start with an optional `v` ([#8303](https://github.com/DataDog/integrations-core/pull/8303))
* Update redis dependency ([#8301](https://github.com/DataDog/integrations-core/pull/8301))

***Fixed***:

* Fix aggregator stub's `assert_histogram_bucket` method ([#8291](https://github.com/DataDog/integrations-core/pull/8291))

## 15.7.2 / 2020-12-23 / Agent 7.25.0

***Fixed***:

* Bump lxml to 4.6.2 ([#8249](https://github.com/DataDog/integrations-core/pull/8249))

## 15.7.1 / 2020-12-15

***Fixed***:

* openmetrics: fix error in label_joins when metrics in label_mapping are not present anymore in active_label_mapping ([#8167](https://github.com/DataDog/integrations-core/pull/8167))

## 15.7.0 / 2020-12-10

***Added***:

* Add `tag_list` column type, allowing to ingest variable-size database-provided tags ([#8147](https://github.com/DataDog/integrations-core/pull/8147))
* Update aerospike dependency ([#8044](https://github.com/DataDog/integrations-core/pull/8044))

***Fixed***:

* Remove unused 'tls_load_default_certs' option ([#8013](https://github.com/DataDog/integrations-core/pull/8013))

## 15.6.1 / 2020-11-10 / Agent 7.24.0

***Fixed***:

* Change DB utils behavior when a truncated row is found to only drop the row ([#7983](https://github.com/DataDog/integrations-core/pull/7983))

## 15.6.0 / 2020-10-31

***Added***:

* Sample the first value of monotonic counts for Open Metrics checks ([#7904](https://github.com/DataDog/integrations-core/pull/7904))
* Support `flush_first_value` flag for monotonic counts ([#7901](https://github.com/DataDog/integrations-core/pull/7901))

***Fixed***:

* Change metadata errors log level ([#7897](https://github.com/DataDog/integrations-core/pull/7897))

## 15.5.0 / 2020-10-30

***Added***:

* Adds support for OPTIONS method ([#7804](https://github.com/DataDog/integrations-core/pull/7804))

***Fixed***:

* Add missing default HTTP headers: Accept, Accept-Encoding ([#7725](https://github.com/DataDog/integrations-core/pull/7725))

## 15.4.0 / 2020-10-28

***Security***:

* Upgrade `cryptography` dependency ([#7869](https://github.com/DataDog/integrations-core/pull/7869))
* Update TUF, in-toto and securesystemslib ([#7844](https://github.com/DataDog/integrations-core/pull/7844))

***Added***:

* Filter metrics by label keys and values ([#7822](https://github.com/DataDog/integrations-core/pull/7822))

## 15.3.0 / 2020-10-28

***Added***:

* [http] Support wildcard subdomain and single wildcard in proxies ([#7767](https://github.com/DataDog/integrations-core/pull/7767))
* Support '*' (match all) in OpenMetrics labels_to_match - allows to apply labels to all timeseries ([#7769](https://github.com/DataDog/integrations-core/pull/7769))

***Fixed***:

* Store english and localized counter classes for reusability ([#7855](https://github.com/DataDog/integrations-core/pull/7855))

## 15.2.0 / 2020-10-27

***Added***:

* Add database statement-level metrics utils ([#7837](https://github.com/DataDog/integrations-core/pull/7837))
* Tracemalloc: Rename white/blacklist to include/exclude ([#7626](https://github.com/DataDog/integrations-core/pull/7626))
* Add a TLSContextWrapper to the base class ([#7812](https://github.com/DataDog/integrations-core/pull/7812))
* Add type checking on PDHBaseCheck ([#7817](https://github.com/DataDog/integrations-core/pull/7817))

## 15.1.0 / 2020-10-20

***Added***:

* Implements token reader for DC/OS Auth JWT token retrieval with login ([#7785](https://github.com/DataDog/integrations-core/pull/7785))
* Make kafka_consumer (kazoo lib) available for Windows ([#7781](https://github.com/DataDog/integrations-core/pull/7781))
* Add support for hashing sequences containing None on Python 3 ([#7779](https://github.com/DataDog/integrations-core/pull/7779))

***Fixed***:

* Fix `AttributeError` when using `additional_metrics` and counter `inst_name` is null ([#7752](https://github.com/DataDog/integrations-core/pull/7752))

## 15.0.0 / 2020-10-13

***Changed***:

* QueryManager - Prevent queries leaking between check instances ([#7750](https://github.com/DataDog/integrations-core/pull/7750))

***Added***:

* Add ability to dynamically get authentication information ([#7660](https://github.com/DataDog/integrations-core/pull/7660))

***Fixed***:

* Update kafka-python to 2.0.2 ([#7718](https://github.com/DataDog/integrations-core/pull/7718))

## 14.0.1 / 2020-09-28 / Agent 7.23.0

***Fixed***:

* Normalize count metric type in `assert_metrics_using_metadata()` ([#7666](https://github.com/DataDog/integrations-core/pull/7666))
* Do not emit insecure warning log for HTTP requests ([#7661](https://github.com/DataDog/integrations-core/pull/7661))

## 14.0.0 / 2020-09-21

***Changed***:

* Replace InsecureRequestWarning with standard logs ([#7512](https://github.com/DataDog/integrations-core/pull/7512))

***Added***:

* New Integration: Snowflake ([#7043](https://github.com/DataDog/integrations-core/pull/7043))
* Add Unix Domain Socket support to RequestsWrapper ([#7585](https://github.com/DataDog/integrations-core/pull/7585))

***Fixed***:

* Better metric names handling when the namespace is empty ([#7567](https://github.com/DataDog/integrations-core/pull/7567))
* Upgrade isort ([#7539](https://github.com/DataDog/integrations-core/pull/7539))
* Add doc for get_check_logger ([#7536](https://github.com/DataDog/integrations-core/pull/7536))

## 13.1.0 / 2020-09-04

***Added***:

* Add the new env parameter to get_subprocess_output ([#7479](https://github.com/DataDog/integrations-core/pull/7479))

## 13.0.0 / 2020-09-01

***Changed***:

* Apply option to ignore InsecureRequestWarning permanently ([#7424](https://github.com/DataDog/integrations-core/pull/7424))

***Added***:

* Add close method to tailer ([#7461](https://github.com/DataDog/integrations-core/pull/7461))
* Add RequestsWrapper option to support UTF-8 for basic auth ([#7441](https://github.com/DataDog/integrations-core/pull/7441))
* Add function to parse RDS tags from the endpoint ([#7353](https://github.com/DataDog/integrations-core/pull/7353))
* Upgrade psutil to 5.7.2 ([#7395](https://github.com/DataDog/integrations-core/pull/7395))

***Fixed***:

* Fix indentation of new "close" method in tailer ([#7463](https://github.com/DataDog/integrations-core/pull/7463))
* Fix style for the latest release of Black ([#7438](https://github.com/DataDog/integrations-core/pull/7438))
* Bump jaydebeapi and jpype1 ([#6963](https://github.com/DataDog/integrations-core/pull/6963))

## 12.0.0 / 2020-08-10 / Agent 7.22.0

***Removed***:

* Remove get_instance_proxy method from base class ([#7036](https://github.com/DataDog/integrations-core/pull/7036))

***Changed***:

* Use requests wrapper and remove httplib2 dependency ([#7247](https://github.com/DataDog/integrations-core/pull/7247))

***Added***:

* Support "*" wildcard in type_overrides configuration ([#7071](https://github.com/DataDog/integrations-core/pull/7071))
* Add `get_check_logger` ([#7126](https://github.com/DataDog/integrations-core/pull/7126))
* Collect metrics from Statistics Messages ([#6945](https://github.com/DataDog/integrations-core/pull/6945))

***Fixed***:

* Ignore empty label_to_hostname label value ([#7232](https://github.com/DataDog/integrations-core/pull/7232))
* Add open file debug log for tailer ([#7205](https://github.com/DataDog/integrations-core/pull/7205))

## 11.12.0 / 2020-06-29 / Agent 7.21.0

***Added***:

* Upgrade pywin32 to 228 ([#6980](https://github.com/DataDog/integrations-core/pull/6980))
* Add MacOS Support ([#6927](https://github.com/DataDog/integrations-core/pull/6927))

## 11.11.1 / 2020-06-17

***Fixed***:

* Gracefully skip quantile-less summary metrics ([#6909](https://github.com/DataDog/integrations-core/pull/6909))

## 11.11.0 / 2020-06-11

***Added***:

* Document openmetrics interface and options ([#6666](https://github.com/DataDog/integrations-core/pull/6666))
* Add methods for the persistent cache Agent interface ([#6819](https://github.com/DataDog/integrations-core/pull/6819))
* Upgrade redis dependency to support `username` in connection strings ([#6708](https://github.com/DataDog/integrations-core/pull/6708))
* Support multiple properties in tag_by ([#6614](https://github.com/DataDog/integrations-core/pull/6614))

## 11.10.0 / 2020-05-25 / Agent 7.20.0

***Added***:

* Override CaseInsensitiveDict `copy()` function ([#6715](https://github.com/DataDog/integrations-core/pull/6715))

## 11.9.0 / 2020-05-20

***Added***:

* Upgrade httplib2 to 0.18.1 ([#6702](https://github.com/DataDog/integrations-core/pull/6702))

***Fixed***:

* Fix time utilities ([#6692](https://github.com/DataDog/integrations-core/pull/6692))

## 11.8.0 / 2020-05-17

***Added***:

* Add utilities for working with time ([#6663](https://github.com/DataDog/integrations-core/pull/6663))
* Upgrade lxml to 4.5.0 ([#6661](https://github.com/DataDog/integrations-core/pull/6661))
* Add send_monotonic_with_gauge config option and refactor test ([#6618](https://github.com/DataDog/integrations-core/pull/6618))
* Add developer docs ([#6623](https://github.com/DataDog/integrations-core/pull/6623))

***Fixed***:

* Update scraper config with instance ([#6664](https://github.com/DataDog/integrations-core/pull/6664))
* Fix thread leak in wmi checks ([#6644](https://github.com/DataDog/integrations-core/pull/6644))

## 11.7.0 / 2020-05-08

***Added***:

* Allow optional dependency installation for all checks ([#6589](https://github.com/DataDog/integrations-core/pull/6589))

***Fixed***:

* Fix a bug that caused win32_event_log integration to hang ([#6576](https://github.com/DataDog/integrations-core/pull/6576))
* Allow to verify that no special hostname was submitted with a metric ([#6529](https://github.com/DataDog/integrations-core/pull/6529))

## 11.6.0 / 2020-04-29

***Added***:

* Validate metrics using metadata.csv ([#6027](https://github.com/DataDog/integrations-core/pull/6027))
* [WinWMICheck] Support latest Agent signature ([#6324](https://github.com/DataDog/integrations-core/pull/6324))

***Fixed***:

* WMI base typing and instance free API ([#6329](https://github.com/DataDog/integrations-core/pull/6329))
* Break reference cycle with log formatter ([#6470](https://github.com/DataDog/integrations-core/pull/6470))
* Mark `instance` as non-`Optional` ([#6350](https://github.com/DataDog/integrations-core/pull/6350))

## 11.5.1 / 2020-05-11 / Agent 7.19.2

***Fixed***:

* Fix a bug that caused win32_event_log integration to hang ([#6576](https://github.com/DataDog/integrations-core/pull/6576))

## 11.5.0 / 2020-04-07 / Agent 7.19.0

***Added***:

* Update PyYAML to 5.3.1 ([#6276](https://github.com/DataDog/integrations-core/pull/6276))

## 11.4.0 / 2020-04-04

***Added***:

* Add option to set SNI hostname via the `Host` header for RequestsWrapper ([#5833](https://github.com/DataDog/integrations-core/pull/5833))
* Upgrade psutil to 5.7.0 ([#6243](https://github.com/DataDog/integrations-core/pull/6243))
* Allow automatic joins to all kube_{object}_labels in KSM check ([#5650](https://github.com/DataDog/integrations-core/pull/5650))
* Allow option to submit histogram/summary sum metric as monotonic count ([#6127](https://github.com/DataDog/integrations-core/pull/6127))
* Add `@metadata_entrypoint` decorator ([#6084](https://github.com/DataDog/integrations-core/pull/6084))
* Add RethinkDB integration ([#5715](https://github.com/DataDog/integrations-core/pull/5715))

***Fixed***:

* Revert `to_native_string` to `to_string` for integrations ([#6238](https://github.com/DataDog/integrations-core/pull/6238))
* Update prometheus_client ([#6200](https://github.com/DataDog/integrations-core/pull/6200))
* Fix failing style checks ([#6207](https://github.com/DataDog/integrations-core/pull/6207))
* Prevent out of bounds on systems with an odd number of counter strings ([#6052](https://github.com/DataDog/integrations-core/pull/6052)) Thanks [AdrianFletcher](https://github.com/AdrianFletcher).
* Update pdh agent signature ([#6162](https://github.com/DataDog/integrations-core/pull/6162))

## 11.3.1 / 2020-03-26

***Fixed***:

* Cast to float before computing temporal percent ([#6146](https://github.com/DataDog/integrations-core/pull/6146))

## 11.3.0 / 2020-03-26

***Added***:

* Use a faster JSON library ([#6143](https://github.com/DataDog/integrations-core/pull/6143))
* Add secrets sanitization helpers ([#6107](https://github.com/DataDog/integrations-core/pull/6107))

## 11.2.0 / 2020-03-24

***Added***:

* Add secrets sanitization helpers ([#6107](https://github.com/DataDog/integrations-core/pull/6107))
* Upgrade `contextlib2` to 0.6.0 ([#6131](https://github.com/DataDog/integrations-core/pull/6131))
* PDH to be able to use new agent signature ([#5936](https://github.com/DataDog/integrations-core/pull/5936))
* Upgrade pyyaml to 5.3 ([#6043](https://github.com/DataDog/integrations-core/pull/6043))
* Upgrade six to 1.14.0 ([#6040](https://github.com/DataDog/integrations-core/pull/6040))
* Expand tracing options and support threads ([#5960](https://github.com/DataDog/integrations-core/pull/5960))
* Add and ship type annotations for base `AgentCheck` class ([#5965](https://github.com/DataDog/integrations-core/pull/5965))
* Make `is_metadata_collection_enabled` static ([#5863](https://github.com/DataDog/integrations-core/pull/5863))
* Improve assertion messages of aggregator stub ([#5975](https://github.com/DataDog/integrations-core/pull/5975))
* Improve aggregator stub's `assert_all_metrics_covered` error message ([#5970](https://github.com/DataDog/integrations-core/pull/5970))
* Mirror Agent's default behavior of `enable_metadata_collection` for `datadog_agent` stub ([#5967](https://github.com/DataDog/integrations-core/pull/5967))
* Upgrade pymqi to 1.10.1 ([#5955](https://github.com/DataDog/integrations-core/pull/5955))

***Fixed***:

* Fix type hints for list-like parameters on `AgentCheck` ([#6105](https://github.com/DataDog/integrations-core/pull/6105))
* Relax type of `ServiceCheck` enum items ([#6064](https://github.com/DataDog/integrations-core/pull/6064))
* Fix type hint on `prefix` argument to `AgentCheck.normalize()` ([#6008](https://github.com/DataDog/integrations-core/pull/6008))
* Explicitly check for event value type before coercing to text ([#5997](https://github.com/DataDog/integrations-core/pull/5997))
* Rename `to_string()` utility to `to_native_string()` ([#5996](https://github.com/DataDog/integrations-core/pull/5996))
* Do not fail on octet stream content type for OpenMetrics ([#5843](https://github.com/DataDog/integrations-core/pull/5843))

## 11.1.0 / 2020-02-26 / Agent 7.18.0

***Added***:

* Bump securesystemslib to 0.14.2 ([#5890](https://github.com/DataDog/integrations-core/pull/5890))

## 11.0.0 / 2020-02-22

***Changed***:

* vSphere new implementation ([#5251](https://github.com/DataDog/integrations-core/pull/5251))
* Make deprecations apparent in UI ([#5530](https://github.com/DataDog/integrations-core/pull/5530))

***Added***:

* Improve performance of pattern matching in OpenMetrics ([#5764](https://github.com/DataDog/integrations-core/pull/5764))
* Add a utility method to check if metadata collection is enabled ([#5748](https://github.com/DataDog/integrations-core/pull/5748))
* Upgrade `aerospike` dependency ([#5779](https://github.com/DataDog/integrations-core/pull/5779))
* Capture python warnings as logs ([#5730](https://github.com/DataDog/integrations-core/pull/5730))
* Make `ignore_metrics` support `*` wildcard for OpenMetrics ([#5759](https://github.com/DataDog/integrations-core/pull/5759))
* Add extra_headers option to http method call ([#5753](https://github.com/DataDog/integrations-core/pull/5753))
* Upgrade kafka-python to 2.0.0 ([#5696](https://github.com/DataDog/integrations-core/pull/5696))
* Support `tls_ignore_warning` at init_config level ([#5657](https://github.com/DataDog/integrations-core/pull/5657))
* Upgrade supervisor dependency ([#5627](https://github.com/DataDog/integrations-core/pull/5627))
* Update in-toto and its deps ([#5599](https://github.com/DataDog/integrations-core/pull/5599))
* Refactor traced decorator and remove wrapt import ([#5586](https://github.com/DataDog/integrations-core/pull/5586))
* Upgrade ddtrace to 0.32.2 ([#5491](https://github.com/DataDog/integrations-core/pull/5491))
* Add new deprecation ([#5539](https://github.com/DataDog/integrations-core/pull/5539))
* Allow deprecation notice strings to be formatted ([#5533](https://github.com/DataDog/integrations-core/pull/5533))
* Add ability to submit time deltas to database query utility ([#5524](https://github.com/DataDog/integrations-core/pull/5524))

***Fixed***:

* Pin enum34 to 1.1.6 ([#5829](https://github.com/DataDog/integrations-core/pull/5829))
* Fix thread leak in WMI sampler ([#5659](https://github.com/DataDog/integrations-core/pull/5659)) Thanks [rlaveycal](https://github.com/rlaveycal).
* Refactor initialization of metric limits ([#5566](https://github.com/DataDog/integrations-core/pull/5566))
* Change wmi_check to use lists instead of tuples for filters ([#5510](https://github.com/DataDog/integrations-core/pull/5510))
* Enforce lazy logging ([#5554](https://github.com/DataDog/integrations-core/pull/5554))
* Properly cast `max_returned_metrics` option to an integer ([#5536](https://github.com/DataDog/integrations-core/pull/5536))
* Install typing dep only for Python 2 ([#5543](https://github.com/DataDog/integrations-core/pull/5543))

## 10.3.0 / 2020-01-21

***Added***:

* [pdh] Make the admin share configurable ([#5485](https://github.com/DataDog/integrations-core/pull/5485))

## 10.2.1 / 2020-01-15

***Fixed***:

* Fix Kubelet credentials handling ([#5455](https://github.com/DataDog/integrations-core/pull/5455))
* Re-introduce legacy cert option handling ([#5443](https://github.com/DataDog/integrations-core/pull/5443))

## 10.2.0 / 2020-01-13

***Added***:

* Update TUF dependency ([#5441](https://github.com/DataDog/integrations-core/pull/5441))
* Make OpenMetrics use the RequestsWrapper ([#5414](https://github.com/DataDog/integrations-core/pull/5414))
* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

***Fixed***:

* Fix http handler ([#5434](https://github.com/DataDog/integrations-core/pull/5434))
* Upgrade vertica to stop logging to /dev/null ([#5352](https://github.com/DataDog/integrations-core/pull/5352))

## 10.1.0 / 2020-01-03

***Added***:

* Move unit conversion helpers to openmetrics mixin ([#5364](https://github.com/DataDog/integrations-core/pull/5364))
* Support metadata and service checks for DB utility ([#5317](https://github.com/DataDog/integrations-core/pull/5317))
* Add and prefer configuring an `auth_type` explicitly on RequestsWrapper ([#5263](https://github.com/DataDog/integrations-core/pull/5263))
* Add support for AWS Signature Version 4 Signing to the RequestsWrapper ([#5249](https://github.com/DataDog/integrations-core/pull/5249))
* Add extra metrics to DB utility ([#5225](https://github.com/DataDog/integrations-core/pull/5225))
* Upgrade `redis` to 3.3.11 ([#5150](https://github.com/DataDog/integrations-core/pull/5150))

***Fixed***:

* Ensure logs are lazily formatted ([#5378](https://github.com/DataDog/integrations-core/pull/5378))
* Remove Agent 5 conditional imports ([#5322](https://github.com/DataDog/integrations-core/pull/5322))
* Only ship `contextlib2` on Python 2 ([#5348](https://github.com/DataDog/integrations-core/pull/5348))
* Lower metadata transformer log level ([#5282](https://github.com/DataDog/integrations-core/pull/5282))
* Update SNMP requirements ([#5234](https://github.com/DataDog/integrations-core/pull/5234))
* Bump psutil to 5.6.7 ([#5210](https://github.com/DataDog/integrations-core/pull/5210))

## 10.0.2 / 2019-12-09 / Agent 7.16.0

***Fixed***:

* Fix normalize for invalid chars and underscore ([#5172](https://github.com/DataDog/integrations-core/pull/5172))

## 10.0.1 / 2019-12-04

***Fixed***:

* Ensure metadata is submitted as strings ([#5139](https://github.com/DataDog/integrations-core/pull/5139))

## 10.0.0 / 2019-12-02

***Changed***:

* Aligns `no_proxy` behavior to general convention ([#5081](https://github.com/DataDog/integrations-core/pull/5081))

## 9.6.0 / 2019-11-28

***Added***:

* Support downloading universal and pure Python wheels ([#4981](https://github.com/DataDog/integrations-core/pull/4981))
* Require boto3 ([#5101](https://github.com/DataDog/integrations-core/pull/5101))
* Add ClickHouse integration ([#4957](https://github.com/DataDog/integrations-core/pull/4957))
* Add database query utilities ([#5045](https://github.com/DataDog/integrations-core/pull/5045))
* Upgrade cryptography to 2.8 ([#5047](https://github.com/DataDog/integrations-core/pull/5047))
* Upgrade pywin32 to 227 ([#5036](https://github.com/DataDog/integrations-core/pull/5036))
* Add SAP HANA integration ([#4502](https://github.com/DataDog/integrations-core/pull/4502))
* Better metadata assertion output ([#4953](https://github.com/DataDog/integrations-core/pull/4953))
* Use a stub class for metadata testing ([#4919](https://github.com/DataDog/integrations-core/pull/4919))
* Extract version utils and use semver for version comparison ([#4844](https://github.com/DataDog/integrations-core/pull/4844))
* Add new version metadata scheme ([#4929](https://github.com/DataDog/integrations-core/pull/4929))
* Add total_time_to_temporal_percent utility ([#4924](https://github.com/DataDog/integrations-core/pull/4924))
* Standardize logging format ([#4906](https://github.com/DataDog/integrations-core/pull/4906))
* Add auth type to RequestsWrapper ([#4708](https://github.com/DataDog/integrations-core/pull/4708))

***Fixed***:

* Fix warnings usage related to RequestsWrapper, Openmetrics and Prometheus ([#5080](https://github.com/DataDog/integrations-core/pull/5080))
* Upgrade psutil dependency to 5.6.5 ([#5059](https://github.com/DataDog/integrations-core/pull/5059))
* Fix no instances case for AgentCheck signature and add more tests ([#4784](https://github.com/DataDog/integrations-core/pull/4784))

## 9.5.0 / 2019-10-22

***Added***:

* Upgrade psycopg2-binary to 2.8.4 ([#4840](https://github.com/DataDog/integrations-core/pull/4840))
* Add mechanism to submit metadata from OpenMetrics checks ([#4757](https://github.com/DataDog/integrations-core/pull/4757))
* Properly fall back to wildcards when defined OpenMetrics transformers do not get a match ([#4757](https://github.com/DataDog/integrations-core/pull/4757))

## 9.4.2 / 2019-10-17 / Agent 6.15.0

***Fixed***:

* Fix RequestsWrapper session `timeout` ([#4811](https://github.com/DataDog/integrations-core/pull/4811))

## 9.4.1 / 2019-10-17

***Fixed***:

* Avoid sending additional gauges for openmetrics histograms if using distribution metrics ([#4780](https://github.com/DataDog/integrations-core/pull/4780))

## 9.4.0 / 2019-10-11

***Deprecated***:

* Add a deprecated warning message to NetworkCheck ([#4560](https://github.com/DataDog/integrations-core/pull/4560))

***Added***:

* Add an option to send histograms/summary counts as monotonic counters ([#4629](https://github.com/DataDog/integrations-core/pull/4629))
* Add option for device testing in e2e ([#4693](https://github.com/DataDog/integrations-core/pull/4693))
* Update self.warning to accept `*args` ([#4731](https://github.com/DataDog/integrations-core/pull/4731))
* Send configuration metadata by default ([#4730](https://github.com/DataDog/integrations-core/pull/4730))
* Add mechanism to execute setup steps before the first check run ([#4713](https://github.com/DataDog/integrations-core/pull/4713))
* Implement Python API for setting check metadata ([#4686](https://github.com/DataDog/integrations-core/pull/4686))
* Upgrade Paramiko to version 2.6.0 ([#4685](https://github.com/DataDog/integrations-core/pull/4685)) Thanks [daniel-savo](https://github.com/daniel-savo).
* Add support for fetching consumer offsets stored in Kafka to `monitor_unlisted_consumer_groups` ([#3957](https://github.com/DataDog/integrations-core/pull/3957)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Support submitting memory profiling metrics during E2E ([#4635](https://github.com/DataDog/integrations-core/pull/4635))
* Add a way to submit non-namespaced metrics and service checks ([#4637](https://github.com/DataDog/integrations-core/pull/4637))
* Add duplication assertion methods to aggregator stub ([#4521](https://github.com/DataDog/integrations-core/pull/4521))
* Add option to override KRB5CCNAME env var ([#4578](https://github.com/DataDog/integrations-core/pull/4578))
* Upgrade pywin32 to 225 ([#4563](https://github.com/DataDog/integrations-core/pull/4563))

***Fixed***:

* Upgrade psutil dependency to 5.6.3 ([#4442](https://github.com/DataDog/integrations-core/pull/4442))

## 9.3.2 / 2019-08-30 / Agent 6.14.0

***Fixed***:

* Update class signature to support the RequestsWrapper ([#4469](https://github.com/DataDog/integrations-core/pull/4469))

## 9.3.1 / 2019-08-28

***Fixed***:

* Fix decumulating bucket on multiple contexts ([#4446](https://github.com/DataDog/integrations-core/pull/4446))

## 9.3.0 / 2019-08-24

***Added***:

* Add each checks' unique ID to logs ([#4410](https://github.com/DataDog/integrations-core/pull/4410))
* Support continuous memory profiling metric submission ([#4409](https://github.com/DataDog/integrations-core/pull/4409))
* Upgrade pyasn1 ([#4289](https://github.com/DataDog/integrations-core/pull/4289))
* Bump Kazoo to 2.6.1 to pull in some minor bugfixes ([#4260](https://github.com/DataDog/integrations-core/pull/4260)) Thanks [jeffwidman](https://github.com/jeffwidman).
* Support memory profiling metrics ([#4239](https://github.com/DataDog/integrations-core/pull/4239))
* Set timeout from init_config in requests wrapper as default ([#4226](https://github.com/DataDog/integrations-core/pull/4226))
* Add the version of an AgentCheck as a property ([#4228](https://github.com/DataDog/integrations-core/pull/4228))
* Upgrade JPype1 to 0.7.0 ([#4211](https://github.com/DataDog/integrations-core/pull/4211))
* Add option for specifying extra headers in RequestsWrapper ([#4208](https://github.com/DataDog/integrations-core/pull/4208))
* Add the ability to debug memory usage ([#4166](https://github.com/DataDog/integrations-core/pull/4166))
* Add tuple timeout format to Request Remapper ([#4172](https://github.com/DataDog/integrations-core/pull/4172))

***Fixed***:

* Remove unused dependencies ([#4405](https://github.com/DataDog/integrations-core/pull/4405))
* Fix http invert without explicit default ([#4277](https://github.com/DataDog/integrations-core/pull/4277))
* Fix prometheus and openmetric unicode labels ([#4157](https://github.com/DataDog/integrations-core/pull/4157))
* Fix openmetrics telemetry memory usage in mixins ([#4193](https://github.com/DataDog/integrations-core/pull/4193))

## 9.2.1 / 2019-07-19 / Agent 6.13.0

***Fixed***:

* Fix openmetrics mixins telemetry metrics ([#4155](https://github.com/DataDog/integrations-core/pull/4155))

## 9.2.0 / 2019-07-19

***Added***:

* Add telemetry metrics counter by ksm collector ([#4125](https://github.com/DataDog/integrations-core/pull/4125))

## 9.1.0 / 2019-07-13

***Added***:

* Telemetry check's metrics ([#4025](https://github.com/DataDog/integrations-core/pull/4025)) Thanks [clamoriniere](https://github.com/clamoriniere).

## 9.0.0 / 2019-07-12

***Changed***:

* Add SSL support for psycopg2, remove pg8000 ([#4096](https://github.com/DataDog/integrations-core/pull/4096))

***Added***:

* Upgrade pymongo to 3.8 ([#4095](https://github.com/DataDog/integrations-core/pull/4095))

***Fixed***:

* Fix label encoding ([#4073](https://github.com/DataDog/integrations-core/pull/4073) and [#4089](https://github.com/DataDog/integrations-core/pull/4089))

## 8.6.0 / 2019-07-09

***Added***:

* Output similar metrics on failed aggregator stub assertions to help debugging ([#4035](https://github.com/DataDog/integrations-core/pull/4035) and [#4076](https://github.com/DataDog/integrations-core/pull/4076))

***Fixed***:

* Avoid WMISampler inheriting from Thread ([#4051](https://github.com/DataDog/integrations-core/pull/4051))

## 8.5.0 / 2019-07-04

***Added***:

* Support SOCKS proxies ([#4021](https://github.com/DataDog/integrations-core/pull/4021))
* Update cryptography version ([#4000](https://github.com/DataDog/integrations-core/pull/4000))
* Add others forms of auth to RequestsWrapper ([#3956](https://github.com/DataDog/integrations-core/pull/3956))
* Add others forms of auth to RequestsWrapper ([#3956](https://github.com/DataDog/integrations-core/pull/3956))
* Better log message for unsafe yaml loading/dumping ([#3771](https://github.com/DataDog/integrations-core/pull/3771))

***Fixed***:

* Make WMISampler hashable ([#4043](https://github.com/DataDog/integrations-core/pull/4043))
* Fix busy loop in WMI implementation ([#4018](https://github.com/DataDog/integrations-core/pull/4018))

## 8.4.1 / 2019-06-29 / Agent 6.12.2

***Fixed***:

* Change WMISampler class to create a single thread, owned by the object ([#3987](https://github.com/DataDog/integrations-core/pull/3987))

## 8.4.0 / 2019-06-18

***Added***:

* Support E2E testing ([#3896](https://github.com/DataDog/integrations-core/pull/3896))

## 8.3.3 / 2019-06-05 / Agent 6.12.0

***Fixed***:

* Revert "[openmetrics] allow blacklisting of strings" ([#3867](https://github.com/DataDog/integrations-core/pull/3867))
* Encode hostname in set_external_tags ([#3866](https://github.com/DataDog/integrations-core/pull/3866))

## 8.3.2 / 2019-06-04

***Fixed***:

* Revert: Properly utilize the provided `metrics_mapper` ([#3861](https://github.com/DataDog/integrations-core/pull/3861))

## 8.3.1 / 2019-06-02

***Fixed***:

* Fix package order of `get_datadog_wheels` ([#3847](https://github.com/DataDog/integrations-core/pull/3847))

## 8.3.0 / 2019-06-01

***Added***:

* [openmetrics] Use Kube service account bearer token for authentication ([#3829](https://github.com/DataDog/integrations-core/pull/3829))

***Fixed***:

* Add upper_bound tag for the total count when collecting histograms buckets ([#3777](https://github.com/DataDog/integrations-core/pull/3777))

## 8.2.0 / 2019-05-21

***Added***:

* Upgrade requests to 2.22.0 ([#3778](https://github.com/DataDog/integrations-core/pull/3778))

## 8.1.0 / 2019-05-14

***Added***:

* Add logging support to RequestsWrapper ([#3737](https://github.com/DataDog/integrations-core/pull/3737))

***Fixed***:

* Fix the initialization of ignored metrics for OpenMetrics ([#3736](https://github.com/DataDog/integrations-core/pull/3736))
* Fixed decoding warning for None tags for python2 check base class ([#3665](https://github.com/DataDog/integrations-core/pull/3665))

## 8.0.0 / 2019-05-06

***Changed***:

* Remove every default header except `User-Agent` ([#3644](https://github.com/DataDog/integrations-core/pull/3644))

***Added***:

* Add easier namespacing for data submission ([#3718](https://github.com/DataDog/integrations-core/pull/3718))
* Upgrade pyyaml to 5.1 ([#3698](https://github.com/DataDog/integrations-core/pull/3698))
* Upgrade psutil dependency to 5.6.2 ([#3684](https://github.com/DataDog/integrations-core/pull/3684))
* Adhere to code style ([#3496](https://github.com/DataDog/integrations-core/pull/3496))
* Upgrade psycopg2-binary to 2.8.2 ([#3649](https://github.com/DataDog/integrations-core/pull/3649))

***Fixed***:

* Improve resiliency of logging initialization phase ([#3705](https://github.com/DataDog/integrations-core/pull/3705))
* Handle more tag decoding errors ([#3671](https://github.com/DataDog/integrations-core/pull/3671))
* Properly utilize the provided `metrics_mapper` ([#3446](https://github.com/DataDog/integrations-core/pull/3446)) Thanks [casidiablo](https://github.com/casidiablo).

## 7.0.0 / 2019-04-18

***Changed***:

* Standardize TLS/SSL protocol naming ([#3620](https://github.com/DataDog/integrations-core/pull/3620))

***Added***:

* Add service_identity dependency ([#3256](https://github.com/DataDog/integrations-core/pull/3256))
* Support Python 3 ([#3605](https://github.com/DataDog/integrations-core/pull/3605))

***Fixed***:

* Parse timeouts as floats in RequestsWrapper ([#3448](https://github.com/DataDog/integrations-core/pull/3448))

## 6.6.1 / 2019-04-04 / Agent 6.11.0

***Fixed***:

* Don't ship `pyodbc` on macOS as SQLServer integration is not shipped on macOS ([#3461](https://github.com/DataDog/integrations-core/pull/3461))

## 6.6.0 / 2019-03-29

***Added***:

* Upgrade in-toto ([#3411](https://github.com/DataDog/integrations-core/pull/3411))
* Support Python 3 ([#3425](https://github.com/DataDog/integrations-core/pull/3425))

## 6.5.0 / 2019-03-29

***Added***:

* Add tagging utility and stub to access the new tagger API ([#3413](https://github.com/DataDog/integrations-core/pull/3413))

## 6.4.0 / 2019-03-22

***Added***:

* Add external_host_tags wrapper to checks_base ([#3316](https://github.com/DataDog/integrations-core/pull/3316))
* Add ability to debug checks with pdb ([#2690](https://github.com/DataDog/integrations-core/pull/2690))
* Add a wrapper for requests ([#3310](https://github.com/DataDog/integrations-core/pull/3310))

***Fixed***:

* Ensure the use of relative imports to avoid circular dependencies ([#3326](https://github.com/DataDog/integrations-core/pull/3326))
* Remove uuid dependency ([#3309](https://github.com/DataDog/integrations-core/pull/3309))
* Properly ship flup on Python 3 ([#3304](https://github.com/DataDog/integrations-core/pull/3304))

## 6.3.0 / 2019-03-14

***Added***:

* Add rfc3339 utilities ([#3189](https://github.com/DataDog/integrations-core/pull/3189))
* Backport Agent V6 utils to the AgentCheck class ([#3261](https://github.com/DataDog/integrations-core/pull/3261))

## 6.2.0 / 2019-03-10

***Added***:

* Upgrade protobuf to 3.7.0 ([#3272](https://github.com/DataDog/integrations-core/pull/3272))
* Upgrade requests to 2.21.0 ([#3274](https://github.com/DataDog/integrations-core/pull/3274))
* Upgrade six to 1.12.0 ([#3276](https://github.com/DataDog/integrations-core/pull/3276))
* Add iter_unique util ([#3269](https://github.com/DataDog/integrations-core/pull/3269))
* Upgrade aerospike dependency ([#3235](https://github.com/DataDog/integrations-core/pull/3235))

***Fixed***:

* Fixed decoding warning for None tags ([#3249](https://github.com/DataDog/integrations-core/pull/3249))
* ensure_unicode with normalize for py3 compatibility ([#3218](https://github.com/DataDog/integrations-core/pull/3218))

## 6.1.0 / 2019-02-20

***Added***:

* Add openstacksdk option to openstack_controller ([#3109](https://github.com/DataDog/integrations-core/pull/3109))

## 6.0.1 / 2019-02-20 / Agent 6.10.0

***Fixed***:

* Import kubernetes lazily to reduce memory footprint ([#3166](https://github.com/DataDog/integrations-core/pull/3166))

## 6.0.0 / 2019-02-12

***Changed***:

* Fix riakcs dependencies ([#3033](https://github.com/DataDog/integrations-core/pull/3033))

***Added***:

* Expose the single check instance as an attribute ([#3093](https://github.com/DataDog/integrations-core/pull/3093))
* Parse raw yaml instances and init_config with dedicated base class method ([#3098](https://github.com/DataDog/integrations-core/pull/3098))
* Add datadog-checks-downloader ([#3026](https://github.com/DataDog/integrations-core/pull/3026))
* Support Python 3 Base WMI ([#3036](https://github.com/DataDog/integrations-core/pull/3036))
* Upgrade psutil ([#3019](https://github.com/DataDog/integrations-core/pull/3019))
* Support Python 3 ([#2835](https://github.com/DataDog/integrations-core/pull/2835))

***Fixed***:

* Resolve flake8 issues ([#3060](https://github.com/DataDog/integrations-core/pull/3060))
* Properly prevent critical logs during testing ([#3053](https://github.com/DataDog/integrations-core/pull/3053))
* Remove extra log about error encoding tag ([#2976](https://github.com/DataDog/integrations-core/pull/2976))
* Improve log messages for when tags aren't utf-8 ([#2966](https://github.com/DataDog/integrations-core/pull/2966))

## 5.2.0 / 2019-01-16

***Added***:

* Make service check statuses available as constants ([#2960](https://github.com/DataDog/integrations-core/pull/2960))

## 5.1.0 / 2019-01-15

***Added***:

* Add round method to checks base ([#2931](https://github.com/DataDog/integrations-core/pull/2931))
* Added lxml dependency ([#2846](https://github.com/DataDog/integrations-core/pull/2846))
* Support unicode for Python 3 bindings ([#2869](https://github.com/DataDog/integrations-core/pull/2869))

***Fixed***:

* Always ensure_unicode for subprocess output ([#2941](https://github.com/DataDog/integrations-core/pull/2941))
* Include count as an aggregate type in tests ([#2920](https://github.com/DataDog/integrations-core/pull/2920))

## 5.0.1 / 2019-01-07 / Agent 6.9.0

***Fixed***:

* Fix context limit logic for OpenMetrics checks ([#2877](https://github.com/DataDog/integrations-core/pull/2877))

## 5.0.0 / 2019-01-04

***Changed***:

* Bump kafka-python and kazoo ([#2766](https://github.com/DataDog/integrations-core/pull/2766))

***Added***:

* Add kube_controller_manager integration ([#2845](https://github.com/DataDog/integrations-core/pull/2845))
* Add kube_leader mixin to monitor leader elections ([#2796](https://github.com/DataDog/integrations-core/pull/2796))
* Prevent caching of PDH counter instances by default ([#2654](https://github.com/DataDog/integrations-core/pull/2654))
* Prevent critical logs during testing ([#2840](https://github.com/DataDog/integrations-core/pull/2840))
* Support trace logging ([#2838](https://github.com/DataDog/integrations-core/pull/2838))
* Bump psycopg2-binary version to 2.7.5 ([#2799](https://github.com/DataDog/integrations-core/pull/2799))
* Support Python 3 ([#2780](https://github.com/DataDog/integrations-core/pull/2780))
* Support Python 3 ([#2738](https://github.com/DataDog/integrations-core/pull/2738))

***Fixed***:

* Use 'format()' function to create device tag ([#2822](https://github.com/DataDog/integrations-core/pull/2822))
* Bump pyodbc for python3.7 compatibility ([#2801](https://github.com/DataDog/integrations-core/pull/2801))
* Fix metric normalization function for Python 3 ([#2784](https://github.com/DataDog/integrations-core/pull/2784))

## 4.6.0 / 2018-12-07 / Agent 6.8.0

***Added***:

* Fix unicode handling of log messages ([#2698](https://github.com/DataDog/integrations-core/pull/2698))

***Fixed***:

* Ensure unicode for subprocess output ([#2697](https://github.com/DataDog/integrations-core/pull/2697))

## 4.5.0 / 2018-12-02

***Added***:

* Improve OpenMetrics label joins ([#2624](https://github.com/DataDog/integrations-core/pull/2624))

## 4.4.0 / 2018-11-30

***Added***:

* Add linux as supported OS ([#2614](https://github.com/DataDog/integrations-core/pull/2614))
* Upgrade cryptography ([#2659](https://github.com/DataDog/integrations-core/pull/2659))
* Upgrade requests ([#2656](https://github.com/DataDog/integrations-core/pull/2656))
* Log line where `AgentCheck.warning` was called in the check ([#2620](https://github.com/DataDog/integrations-core/pull/2620))

***Fixed***:

* Fix not_asserted aggregator stub function ([#2639](https://github.com/DataDog/integrations-core/pull/2639))
* Fix requirements-agent-release.txt updating ([#2617](https://github.com/DataDog/integrations-core/pull/2617))

## 4.3.0 / 2018-11-12

***Added***:

* Add option to prevent subprocess command logging ([#2565](https://github.com/DataDog/integrations-core/pull/2565))
* Support Kerberos auth ([#2516](https://github.com/DataDog/integrations-core/pull/2516))
* Add option to send additional metric tags for Open Metrics ([#2514](https://github.com/DataDog/integrations-core/pull/2514))
* Add standard ssl_verify option to Open Metrics ([#2507](https://github.com/DataDog/integrations-core/pull/2507))
* Winpdh improve exception messages ([#2486](https://github.com/DataDog/integrations-core/pull/2486))
* Upgrade requests ([#2481](https://github.com/DataDog/integrations-core/pull/2481))
* Fix unicode handling on A6 ([#2435](https://github.com/DataDog/integrations-core/pull/2435))

***Fixed***:

* Fix bug making the network check read /proc instead of /host/proc on containers ([#2460](https://github.com/DataDog/integrations-core/pull/2460))

## 4.2.0 / 2018-10-16 / Agent 6.6.0

***Added***:

* Expose text conversion methods ([#2420](https://github.com/DataDog/integrations-core/pull/2420))

***Fixed***:

* Handle unicode strings in non-float handler's error message ([#2419](https://github.com/DataDog/integrations-core/pull/2419))

## 4.1.0 / 2018-10-12

***Added***:

* Expose core functionality at the root ([#2394](https://github.com/DataDog/integrations-core/pull/2394))
* base: add check name to Limiter warning message ([#2391](https://github.com/DataDog/integrations-core/pull/2391))

***Fixed***:

* Fix import of _get_py_loglevel ([#2383](https://github.com/DataDog/integrations-core/pull/2383))
* Fix hostname override and type for status_report.count metrics ([#2372](https://github.com/DataDog/integrations-core/pull/2372))

## 4.0.0 / 2018-10-11

***Changed***:

* Add base subpackage to datadog_checks_base ([#2331](https://github.com/DataDog/integrations-core/pull/2331))

***Added***:

* Added generic error class ConfigurationError ([#2367](https://github.com/DataDog/integrations-core/pull/2367))
* Freeze Agent requirements ([#2328](https://github.com/DataDog/integrations-core/pull/2328))
* Pin pywin32 dependency ([#2322](https://github.com/DataDog/integrations-core/pull/2322))

## 3.0.0 / 2018-09-25

***Changed***:

* Catch exception when string sent as metric value ([#2293](https://github.com/DataDog/integrations-core/pull/2293))
* Revert default prometheus metric limit to 2000 ([#2248](https://github.com/DataDog/integrations-core/pull/2248))

***Added***:

* Adds ability to Trace "check" function with DD APM ([#2079](https://github.com/DataDog/integrations-core/pull/2079))

***Fixed***:

* Fix base class imports for Agent 5 ([#2232](https://github.com/DataDog/integrations-core/pull/2232))

## 2.2.1 / 2018-09-11 / Agent 6.5.0

***Fixed***:

* Temporarily increase the limit of prometheus metrics sent for 6.5 ([#2214](https://github.com/DataDog/integrations-core/pull/2214))

## 2.2.0 / 2018-09-06

***Changed***:

* Freeze pyVmomi dep in base check ([#2181](https://github.com/DataDog/integrations-core/pull/2181))

## 2.1.0 / 2018-09-05

***Changed***:

* Change order of precedence of whitelist and blacklist for pattern filtering ([#2174](https://github.com/DataDog/integrations-core/pull/2174))

## 2.0.0 / 2018-09-04

***Changed***:

* Allow checks to manually specify in their configuration which defaults to use ([#2145](https://github.com/DataDog/integrations-core/pull/2145))
* Use different defaults if scraper_config is created by OpenMetricsBaseCheck ([#2135](https://github.com/DataDog/integrations-core/pull/2135))
* Drop protobuf support for OpenMetrics ([#2098](https://github.com/DataDog/integrations-core/pull/2098))
* Create OpenMetricsBaseCheck, an improved version of GenericPrometheusCheck ([#1976](https://github.com/DataDog/integrations-core/pull/1976))

***Added***:

* Add cluster-name suffix to node-names in kubernetes state ([#2069](https://github.com/DataDog/integrations-core/pull/2069))
* Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default ([#2093](https://github.com/DataDog/integrations-core/pull/2093))
* Add code coverage ([#2105](https://github.com/DataDog/integrations-core/pull/2105))

***Fixed***:

* Moves WMI Check to Pytest ([#2133](https://github.com/DataDog/integrations-core/pull/2133))
* Fix Prometheus scraping for Python 3 ([#2128](https://github.com/DataDog/integrations-core/pull/2128))
* Move RiakCS to pytest, fixes duped tags in RiakCS, adds google_cloud_engine pip dep ([#2081](https://github.com/DataDog/integrations-core/pull/2081))

## 1.5.0 / 2018-08-19

***Added***:

* Allow installation of base dependencies ([#2067](https://github.com/DataDog/integrations-core/pull/2067))
* Support Python 3 for datadog_checks_base ([#1957](https://github.com/DataDog/integrations-core/pull/1957))

***Fixed***:

* Retrieve no_proxy directly from the Datadog Agent's configuration ([#2004](https://github.com/DataDog/integrations-core/pull/2004))
* Properly skip proxy environment variables ([#1935](https://github.com/DataDog/integrations-core/pull/1935))
* Update cryptography to 2.3 ([#1927](https://github.com/DataDog/integrations-core/pull/1927))

## 1.4.0 / 2018-07-18 / Agent 6.4.0

***Changed***:

* Bump prometheus client library to 0.3.0 ([#1866](https://github.com/DataDog/integrations-core/pull/1866))

***Added***:

* Make HTTP request timeout configurable in prometheus checks ([#1790](https://github.com/DataDog/integrations-core/pull/1790))

***Fixed***:

* fix packaging of agent requirements ([#1911](https://github.com/DataDog/integrations-core/pull/1911))
* Properly use skip_proxy for instance configuration ([#1880](https://github.com/DataDog/integrations-core/pull/1880))
* Sync WMI utils from dd-agent to datadog-checks-base ([#1897](https://github.com/DataDog/integrations-core/pull/1897))
* Improve check performance by filtering it's input before parsing ([#1875](https://github.com/DataDog/integrations-core/pull/1875))

## 1.3.2 / 2018-06-15

***Changed***:

* Bump requests to 2.19.1 ([#1743](https://github.com/DataDog/integrations-core/pull/1743))

## 1.3.1 / 2018-06-13

***Changed***:

* Set requests stream option to false when scraping Prometheus endpoints ([#1596](https://github.com/DataDog/integrations-core/pull/1596))

***Fixed***:

* upgrade requests dependency ([#1734](https://github.com/DataDog/integrations-core/pull/1734))

## 1.3.0 / 2018-06-07

***Added***:

* Support for gathering metrics from prometheus endpoint for the kubelet itself. ([#1581](https://github.com/DataDog/integrations-core/pull/1581))
* include wmi for compat ([#1565](https://github.com/DataDog/integrations-core/pull/1565))
* added missing tailfile util ([#1566](https://github.com/DataDog/integrations-core/pull/1566))

***Fixed***:

* change default value of AgentCheck.check_id for Agent 6 ([#1652](https://github.com/DataDog/integrations-core/pull/1652))
* [base] when running A6, mirror logging behavior ([#1561](https://github.com/DataDog/integrations-core/pull/1561))

## 1.2.2 / 2018-05-11

***Added***:

* The generic Prometheus check will now send counter as monotonic counter.
* Discard metrics with invalid values

***Fixed***:

* Prometheus requests can use an insecure option
* Correctly handle missing counters/strings in PDH checks when possible
* Fix Prometheus Scrapper logger
* Clean-up export for `PDHBaseCheck` + export `WinPDHCounter`. [#1183](https://github.com/DataDog/integrations-core/issues/1183)

## 1.2.1 / 2018-03-23

***Added***:

* Keep track of Service Checks in the Aggregator stub.

***Fixed***:

* Correctly handle internationalized versions of Windows in the PDH library.

## 1.1.0 / 2018-03-23

***Added***:

* Add a generic prometheus check base class & rework prometheus check using a mixin

## 1.0.0 / 2017-03-22

***Added***:

* adds `datadog_checks`
