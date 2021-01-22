# CHANGELOG - datadog_checks_base

## 16.1.0 / 2021-01-22

* [Added] Add new version of OpenMetrics base class. See [#8300](https://github.com/DataDog/integrations-core/pull/8300).
* [Fixed] Properly support check namespacing for the `submit_histogram_bucket` method. See [#8390](https://github.com/DataDog/integrations-core/pull/8390).

## 16.0.0 / 2021-01-13

* [Added] Add `no_op` utility. See [#8356](https://github.com/DataDog/integrations-core/pull/8356).
* [Added] Support tags set at runtime on the DB QueryManager. See [#8304](https://github.com/DataDog/integrations-core/pull/8304).
* [Added] Add the `host` tag to RDS instances' parsed tags. See [#8292](https://github.com/DataDog/integrations-core/pull/8292).
* [Added] Update prometheus mixin to use the request wrapper. See [#8223](https://github.com/DataDog/integrations-core/pull/8223).
* [Added] Add optional argument for overriding get_tls_context() parameters. See [#8275](https://github.com/DataDog/integrations-core/pull/8275).
* [Added] Allow semver version metadata to start with an optional `v`. See [#8303](https://github.com/DataDog/integrations-core/pull/8303).
* [Added] Update redis dependency. See [#8301](https://github.com/DataDog/integrations-core/pull/8301).
* [Fixed] Fix aggregator stub's `assert_histogram_bucket` method. See [#8291](https://github.com/DataDog/integrations-core/pull/8291).
* [Removed] Remove unneccessary `pytz` dependency. See [#8354](https://github.com/DataDog/integrations-core/pull/8354).

## 15.7.2 / 2020-12-23 / Agent 7.25.0

* [Fixed] Bump lxml to 4.6.2. See [#8249](https://github.com/DataDog/integrations-core/pull/8249).

## 15.7.1 / 2020-12-15

* [Fixed] openmetrics: fix error in label_joins when metrics in label_mapping are not present anymore in active_label_mapping. See [#8167](https://github.com/DataDog/integrations-core/pull/8167).

## 15.7.0 / 2020-12-10

* [Added] Add `tag_list` column type, allowing to ingest variable-size database-provided tags. See [#8147](https://github.com/DataDog/integrations-core/pull/8147).
* [Added] Update aerospike dependency. See [#8044](https://github.com/DataDog/integrations-core/pull/8044).
* [Fixed] Remove unused 'tls_load_default_certs' option. See [#8013](https://github.com/DataDog/integrations-core/pull/8013).

## 15.6.1 / 2020-11-10 / Agent 7.24.0

* [Fixed] Change DB utils behavior when a truncated row is found to only drop the row. See [#7983](https://github.com/DataDog/integrations-core/pull/7983).

## 15.6.0 / 2020-10-31

* [Added] Sample the first value of monotonic counts for Open Metrics checks. See [#7904](https://github.com/DataDog/integrations-core/pull/7904).
* [Added] Support `flush_first_value` flag for monotonic counts. See [#7901](https://github.com/DataDog/integrations-core/pull/7901).
* [Fixed] Change metadata errors log level. See [#7897](https://github.com/DataDog/integrations-core/pull/7897).

## 15.5.0 / 2020-10-30

* [Added] Adds support for OPTIONS method. See [#7804](https://github.com/DataDog/integrations-core/pull/7804).
* [Fixed] Add missing default HTTP headers: Accept, Accept-Encoding. See [#7725](https://github.com/DataDog/integrations-core/pull/7725).

## 15.4.0 / 2020-10-28

* [Added] Filter metrics by label keys and values. See [#7822](https://github.com/DataDog/integrations-core/pull/7822).
* [Security] Upgrade `cryptography` dependency. See [#7869](https://github.com/DataDog/integrations-core/pull/7869).
* [Security] Update TUF, in-toto and securesystemslib. See [#7844](https://github.com/DataDog/integrations-core/pull/7844).

## 15.3.0 / 2020-10-28

* [Added] [http] Support wildcard subdomain and single wildcard in proxies. See [#7767](https://github.com/DataDog/integrations-core/pull/7767).
* [Added] Support '*' (match all) in OpenMetrics labels_to_match - allows to apply labels to all timeseries. See [#7769](https://github.com/DataDog/integrations-core/pull/7769).
* [Fixed] Store english and localized counter classes for reusability. See [#7855](https://github.com/DataDog/integrations-core/pull/7855).

## 15.2.0 / 2020-10-27

* [Added] Add database statement-level metrics utils. See [#7837](https://github.com/DataDog/integrations-core/pull/7837).
* [Added] Tracemalloc: Rename white/blacklist to include/exclude. See [#7626](https://github.com/DataDog/integrations-core/pull/7626).
* [Added] Add a TLSContextWrapper to the base class. See [#7812](https://github.com/DataDog/integrations-core/pull/7812).
* [Added] Add type checking on PDHBaseCheck. See [#7817](https://github.com/DataDog/integrations-core/pull/7817).

## 15.1.0 / 2020-10-20

* [Added] Implements token reader for DC/OS Auth JWT token retrieval with login. See [#7785](https://github.com/DataDog/integrations-core/pull/7785).
* [Added] Make kafka_consumer (kazoo lib) available for Windows. See [#7781](https://github.com/DataDog/integrations-core/pull/7781).
* [Added] Add support for hashing sequences containing None on Python 3. See [#7779](https://github.com/DataDog/integrations-core/pull/7779).
* [Fixed] Fix `AttributeError` when using `additional_metrics` and counter `inst_name` is null. See [#7752](https://github.com/DataDog/integrations-core/pull/7752).

## 15.0.0 / 2020-10-13

* [Added] Add ability to dynamically get authentication information. See [#7660](https://github.com/DataDog/integrations-core/pull/7660).
* [Fixed] Update kafka-python to 2.0.2. See [#7718](https://github.com/DataDog/integrations-core/pull/7718).
* [Changed] QueryManager - Prevent queries leaking between check instances. See [#7750](https://github.com/DataDog/integrations-core/pull/7750).

## 14.0.1 / 2020-09-28 / Agent 7.23.0

* [Fixed] Normalize count metric type in `assert_metrics_using_metadata()`. See [#7666](https://github.com/DataDog/integrations-core/pull/7666).
* [Fixed] Do not emit insecure warning log for HTTP requests. See [#7661](https://github.com/DataDog/integrations-core/pull/7661).

## 14.0.0 / 2020-09-21

* [Added] New Integration: Snowflake. See [#7043](https://github.com/DataDog/integrations-core/pull/7043).
* [Added] Add Unix Domain Socket support to RequestsWrapper. See [#7585](https://github.com/DataDog/integrations-core/pull/7585).
* [Fixed] Better metric names handling when the namespace is empty. See [#7567](https://github.com/DataDog/integrations-core/pull/7567).
* [Fixed] Upgrade isort. See [#7539](https://github.com/DataDog/integrations-core/pull/7539).
* [Fixed] Add doc for get_check_logger. See [#7536](https://github.com/DataDog/integrations-core/pull/7536).
* [Changed] Replace InsecureRequestWarning with standard logs. See [#7512](https://github.com/DataDog/integrations-core/pull/7512).

## 13.1.0 / 2020-09-04

* [Added] Add the new env parameter to get_subprocess_output. See [#7479](https://github.com/DataDog/integrations-core/pull/7479).

## 13.0.0 / 2020-09-01

* [Fixed] Fix indentation of new "close" method in tailer. See [#7463](https://github.com/DataDog/integrations-core/pull/7463).
* [Added] Add close method to tailer. See [#7461](https://github.com/DataDog/integrations-core/pull/7461).
* [Added] Add RequestsWrapper option to support UTF-8 for basic auth. See [#7441](https://github.com/DataDog/integrations-core/pull/7441).
* [Added] Add function to parse RDS tags from the endpoint. See [#7353](https://github.com/DataDog/integrations-core/pull/7353).
* [Added] Upgrade psutil to 5.7.2. See [#7395](https://github.com/DataDog/integrations-core/pull/7395).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).
* [Fixed] Bump jaydebeapi and jpype1. See [#6963](https://github.com/DataDog/integrations-core/pull/6963).
* [Changed] Apply option to ignore InsecureRequestWarning permanently. See [#7424](https://github.com/DataDog/integrations-core/pull/7424).

## 12.0.0 / 2020-08-10 / Agent 7.22.0

* [Added] Support "*" wildcard in type_overrides configuration. See [#7071](https://github.com/DataDog/integrations-core/pull/7071).
* [Added] Add `get_check_logger`. See [#7126](https://github.com/DataDog/integrations-core/pull/7126).
* [Added] Collect metrics from Statistics Messages. See [#6945](https://github.com/DataDog/integrations-core/pull/6945).
* [Fixed] Ignore empty label_to_hostname label value. See [#7232](https://github.com/DataDog/integrations-core/pull/7232).
* [Fixed] Add open file debug log for tailer. See [#7205](https://github.com/DataDog/integrations-core/pull/7205).
* [Changed] Use requests wrapper and remove httplib2 dependency. See [#7247](https://github.com/DataDog/integrations-core/pull/7247).
* [Removed] Remove get_instance_proxy method from base class. See [#7036](https://github.com/DataDog/integrations-core/pull/7036).

## 11.12.0 / 2020-06-29 / Agent 7.21.0

* [Added] Upgrade pywin32 to 228. See [#6980](https://github.com/DataDog/integrations-core/pull/6980).
* [Added] Add MacOS Support. See [#6927](https://github.com/DataDog/integrations-core/pull/6927).

## 11.11.1 / 2020-06-17

* [Fixed] Gracefully skip quantile-less summary metrics. See [#6909](https://github.com/DataDog/integrations-core/pull/6909).

## 11.11.0 / 2020-06-11

* [Added] Document openmetrics interface and options. See [#6666](https://github.com/DataDog/integrations-core/pull/6666).
* [Added] Add methods for the persistent cache Agent interface. See [#6819](https://github.com/DataDog/integrations-core/pull/6819).
* [Added] Upgrade redis dependency to support `username` in connection strings. See [#6708](https://github.com/DataDog/integrations-core/pull/6708).
* [Added] Support multiple properties in tag_by. See [#6614](https://github.com/DataDog/integrations-core/pull/6614).

## 11.10.0 / 2020-05-25 / Agent 7.20.0

* [Added] Override CaseInsensitiveDict `copy()` function. See [#6715](https://github.com/DataDog/integrations-core/pull/6715).

## 11.9.0 / 2020-05-20

* [Added] Upgrade httplib2 to 0.18.1. See [#6702](https://github.com/DataDog/integrations-core/pull/6702).
* [Fixed] Fix time utilities. See [#6692](https://github.com/DataDog/integrations-core/pull/6692).

## 11.8.0 / 2020-05-17

* [Added] Add utilities for working with time. See [#6663](https://github.com/DataDog/integrations-core/pull/6663).
* [Added] Upgrade lxml to 4.5.0. See [#6661](https://github.com/DataDog/integrations-core/pull/6661).
* [Added] Add send_monotonic_with_gauge config option and refactor test. See [#6618](https://github.com/DataDog/integrations-core/pull/6618).
* [Added] Add developer docs. See [#6623](https://github.com/DataDog/integrations-core/pull/6623).
* [Fixed] Update scraper config with instance. See [#6664](https://github.com/DataDog/integrations-core/pull/6664).
* [Fixed] Fix thread leak in wmi checks. See [#6644](https://github.com/DataDog/integrations-core/pull/6644).

## 11.7.0 / 2020-05-08

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).
* [Fixed] Fix a bug that caused win32_event_log integration to hang. See [#6576](https://github.com/DataDog/integrations-core/pull/6576).
* [Fixed] Allow to verify that no special hostname was submitted with a metric. See [#6529](https://github.com/DataDog/integrations-core/pull/6529).

## 11.6.0 / 2020-04-29

* [Added] Validate metrics using metadata.csv. See [#6027](https://github.com/DataDog/integrations-core/pull/6027).
* [Added] [WinWMICheck] Support latest Agent signature. See [#6324](https://github.com/DataDog/integrations-core/pull/6324).
* [Fixed] WMI base typing and instance free API. See [#6329](https://github.com/DataDog/integrations-core/pull/6329).
* [Fixed] Break reference cycle with log formatter. See [#6470](https://github.com/DataDog/integrations-core/pull/6470).
* [Fixed] Mark `instance` as non-`Optional`. See [#6350](https://github.com/DataDog/integrations-core/pull/6350).

## 11.5.1 / 2020-05-11 / Agent 7.19.2

* [Fixed] Fix a bug that caused win32_event_log integration to hang. See [#6576](https://github.com/DataDog/integrations-core/pull/6576).

## 11.5.0 / 2020-04-07 / Agent 7.19.0

* [Added] Update PyYAML to 5.3.1. See [#6276](https://github.com/DataDog/integrations-core/pull/6276).

## 11.4.0 / 2020-04-04

* [Added] Add option to set SNI hostname via the `Host` header for RequestsWrapper. See [#5833](https://github.com/DataDog/integrations-core/pull/5833).
* [Added] Upgrade psutil to 5.7.0. See [#6243](https://github.com/DataDog/integrations-core/pull/6243).
* [Added] Allow automatic joins to all kube_{object}_labels in KSM check. See [#5650](https://github.com/DataDog/integrations-core/pull/5650).
* [Added] Allow option to submit histogram/summary sum metric as monotonic count. See [#6127](https://github.com/DataDog/integrations-core/pull/6127).
* [Added] Add `@metadata_entrypoint` decorator. See [#6084](https://github.com/DataDog/integrations-core/pull/6084).
* [Added] Add RethinkDB integration. See [#5715](https://github.com/DataDog/integrations-core/pull/5715).
* [Fixed] Revert `to_native_string` to `to_string` for integrations. See [#6238](https://github.com/DataDog/integrations-core/pull/6238).
* [Fixed] Update prometheus_client. See [#6200](https://github.com/DataDog/integrations-core/pull/6200).
* [Fixed] Fix failing style checks. See [#6207](https://github.com/DataDog/integrations-core/pull/6207).
* [Fixed] Prevent out of bounds on systems with an odd number of counter strings. See [#6052](https://github.com/DataDog/integrations-core/pull/6052). Thanks [AdrianFletcher](https://github.com/AdrianFletcher).
* [Fixed] Update pdh agent signature. See [#6162](https://github.com/DataDog/integrations-core/pull/6162).

## 11.3.1 / 2020-03-26

* [Fixed] Cast to float before computing temporal percent. See [#6146](https://github.com/DataDog/integrations-core/pull/6146).

## 11.3.0 / 2020-03-26

* [Added] Use a faster JSON library. See [#6143](https://github.com/DataDog/integrations-core/pull/6143).
* [Added] Add secrets sanitization helpers. See [#6107](https://github.com/DataDog/integrations-core/pull/6107).

## 11.2.0 / 2020-03-24

* [Added] Add secrets sanitization helpers. See [#6107](https://github.com/DataDog/integrations-core/pull/6107).
* [Added] Upgrade `contextlib2` to 0.6.0. See [#6131](https://github.com/DataDog/integrations-core/pull/6131).
* [Added] PDH to be able to use new agent signature. See [#5936](https://github.com/DataDog/integrations-core/pull/5936).
* [Added] Upgrade pyyaml to 5.3. See [#6043](https://github.com/DataDog/integrations-core/pull/6043).
* [Added] Upgrade six to 1.14.0. See [#6040](https://github.com/DataDog/integrations-core/pull/6040).
* [Added] Expand tracing options and support threads. See [#5960](https://github.com/DataDog/integrations-core/pull/5960).
* [Added] Add and ship type annotations for base `AgentCheck` class. See [#5965](https://github.com/DataDog/integrations-core/pull/5965).
* [Added] Make `is_metadata_collection_enabled` static. See [#5863](https://github.com/DataDog/integrations-core/pull/5863).
* [Added] Improve assertion messages of aggregator stub. See [#5975](https://github.com/DataDog/integrations-core/pull/5975).
* [Added] Improve aggregator stub's `assert_all_metrics_covered` error message. See [#5970](https://github.com/DataDog/integrations-core/pull/5970).
* [Added] Mirror Agent's default behavior of `enable_metadata_collection` for `datadog_agent` stub. See [#5967](https://github.com/DataDog/integrations-core/pull/5967).
* [Added] Upgrade pymqi to 1.10.1. See [#5955](https://github.com/DataDog/integrations-core/pull/5955).
* [Fixed] Fix type hints for list-like parameters on `AgentCheck`. See [#6105](https://github.com/DataDog/integrations-core/pull/6105).
* [Fixed] Relax type of `ServiceCheck` enum items. See [#6064](https://github.com/DataDog/integrations-core/pull/6064).
* [Fixed] Fix type hint on `prefix` argument to `AgentCheck.normalize()`. See [#6008](https://github.com/DataDog/integrations-core/pull/6008).
* [Fixed] Explicitly check for event value type before coercing to text. See [#5997](https://github.com/DataDog/integrations-core/pull/5997).
* [Fixed] Rename `to_string()` utility to `to_native_string()`. See [#5996](https://github.com/DataDog/integrations-core/pull/5996).
* [Fixed] Do not fail on octet stream content type for OpenMetrics. See [#5843](https://github.com/DataDog/integrations-core/pull/5843).

## 11.1.0 / 2020-02-26 / Agent 7.18.0

* [Added] Bump securesystemslib to 0.14.2. See [#5890](https://github.com/DataDog/integrations-core/pull/5890).

## 11.0.0 / 2020-02-22

* [Fixed] Pin enum34 to 1.1.6. See [#5829](https://github.com/DataDog/integrations-core/pull/5829).
* [Fixed] Fix thread leak in WMI sampler. See [#5659](https://github.com/DataDog/integrations-core/pull/5659). Thanks [rlaveycal](https://github.com/rlaveycal).
* [Added] Improve performance of pattern matching in OpenMetrics. See [#5764](https://github.com/DataDog/integrations-core/pull/5764).
* [Added] Add a utility method to check if metadata collection is enabled. See [#5748](https://github.com/DataDog/integrations-core/pull/5748).
* [Added] Upgrade `aerospike` dependency. See [#5779](https://github.com/DataDog/integrations-core/pull/5779).
* [Added] Capture python warnings as logs. See [#5730](https://github.com/DataDog/integrations-core/pull/5730).
* [Added] Make `ignore_metrics` support `*` wildcard for OpenMetrics. See [#5759](https://github.com/DataDog/integrations-core/pull/5759).
* [Added] Add extra_headers option to http method call. See [#5753](https://github.com/DataDog/integrations-core/pull/5753).
* [Added] Upgrade kafka-python to 2.0.0. See [#5696](https://github.com/DataDog/integrations-core/pull/5696).
* [Fixed] Refactor initialization of metric limits. See [#5566](https://github.com/DataDog/integrations-core/pull/5566).
* [Added] Support `tls_ignore_warning` at init_config level. See [#5657](https://github.com/DataDog/integrations-core/pull/5657).
* [Changed] vSphere new implementation. See [#5251](https://github.com/DataDog/integrations-core/pull/5251).
* [Added] Upgrade supervisor dependency. See [#5627](https://github.com/DataDog/integrations-core/pull/5627).
* [Added] Update in-toto and its deps. See [#5599](https://github.com/DataDog/integrations-core/pull/5599).
* [Added] Refactor traced decorator and remove wrapt import. See [#5586](https://github.com/DataDog/integrations-core/pull/5586).
* [Fixed] Change wmi_check to use lists instead of tuples for filters. See [#5510](https://github.com/DataDog/integrations-core/pull/5510).
* [Added] Upgrade ddtrace to 0.32.2. See [#5491](https://github.com/DataDog/integrations-core/pull/5491).
* [Fixed] Enforce lazy logging. See [#5554](https://github.com/DataDog/integrations-core/pull/5554).
* [Fixed] Properly cast `max_returned_metrics` option to an integer. See [#5536](https://github.com/DataDog/integrations-core/pull/5536).
* [Fixed] Install typing dep only for Python 2. See [#5543](https://github.com/DataDog/integrations-core/pull/5543).
* [Added] Add new deprecation. See [#5539](https://github.com/DataDog/integrations-core/pull/5539).
* [Added] Allow deprecation notice strings to be formatted. See [#5533](https://github.com/DataDog/integrations-core/pull/5533).
* [Changed] Make deprecations apparent in UI. See [#5530](https://github.com/DataDog/integrations-core/pull/5530).
* [Added] Add ability to submit time deltas to database query utility. See [#5524](https://github.com/DataDog/integrations-core/pull/5524).

## 10.3.0 / 2020-01-21

* [Added] [pdh] Make the admin share configurable. See [#5485](https://github.com/DataDog/integrations-core/pull/5485).

## 10.2.1 / 2020-01-15

* [Fixed] Fix Kubelet credentials handling. See [#5455](https://github.com/DataDog/integrations-core/pull/5455).
* [Fixed] Re-introduce legacy cert option handling. See [#5443](https://github.com/DataDog/integrations-core/pull/5443).

## 10.2.0 / 2020-01-13

* [Added] Update TUF dependency. See [#5441](https://github.com/DataDog/integrations-core/pull/5441).
* [Fixed] Fix http handler. See [#5434](https://github.com/DataDog/integrations-core/pull/5434).
* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).
* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Fixed] Upgrade vertica to stop logging to /dev/null. See [#5352](https://github.com/DataDog/integrations-core/pull/5352).

## 10.1.0 / 2020-01-03

* [Fixed] Ensure logs are lazily formatted. See [#5378](https://github.com/DataDog/integrations-core/pull/5378).
* [Fixed] Remove Agent 5 conditional imports. See [#5322](https://github.com/DataDog/integrations-core/pull/5322).
* [Added] Move unit conversion helpers to openmetrics mixin. See [#5364](https://github.com/DataDog/integrations-core/pull/5364).
* [Fixed] Only ship `contextlib2` on Python 2. See [#5348](https://github.com/DataDog/integrations-core/pull/5348).
* [Added] Support metadata and service checks for DB utility. See [#5317](https://github.com/DataDog/integrations-core/pull/5317).
* [Added] Add and prefer configuring an `auth_type` explicitly on RequestsWrapper. See [#5263](https://github.com/DataDog/integrations-core/pull/5263).
* [Fixed] Lower metadata transformer log level. See [#5282](https://github.com/DataDog/integrations-core/pull/5282).
* [Added] Add support for AWS Signature Version 4 Signing to the RequestsWrapper. See [#5249](https://github.com/DataDog/integrations-core/pull/5249).
* [Added] Add extra metrics to DB utility. See [#5225](https://github.com/DataDog/integrations-core/pull/5225).
* [Added] Upgrade `redis` to 3.3.11. See [#5150](https://github.com/DataDog/integrations-core/pull/5150).
* [Fixed] Update SNMP requirements. See [#5234](https://github.com/DataDog/integrations-core/pull/5234).
* [Fixed] Bump psutil to 5.6.7. See [#5210](https://github.com/DataDog/integrations-core/pull/5210).

## 10.0.2 / 2019-12-09 / Agent 7.16.0

* [Fixed] Fix normalize for invalid chars and underscore. See [#5172](https://github.com/DataDog/integrations-core/pull/5172).

## 10.0.1 / 2019-12-04

* [Fixed] Ensure metadata is submitted as strings. See [#5139](https://github.com/DataDog/integrations-core/pull/5139).

## 10.0.0 / 2019-12-02

* [Changed] Aligns `no_proxy` behavior to general convention. See [#5081](https://github.com/DataDog/integrations-core/pull/5081).

## 9.6.0 / 2019-11-28

* [Added] Support downloading universal and pure Python wheels. See [#4981](https://github.com/DataDog/integrations-core/pull/4981).
* [Added] Require boto3. See [#5101](https://github.com/DataDog/integrations-core/pull/5101).
* [Fixed] Fix warnings usage related to RequestsWrapper, Openmetrics and Prometheus. See [#5080](https://github.com/DataDog/integrations-core/pull/5080).
* [Fixed] Upgrade psutil dependency to 5.6.5. See [#5059](https://github.com/DataDog/integrations-core/pull/5059).
* [Added] Add ClickHouse integration. See [#4957](https://github.com/DataDog/integrations-core/pull/4957).
* [Added] Add database query utilities. See [#5045](https://github.com/DataDog/integrations-core/pull/5045).
* [Added] Upgrade cryptography to 2.8. See [#5047](https://github.com/DataDog/integrations-core/pull/5047).
* [Added] Upgrade pywin32 to 227. See [#5036](https://github.com/DataDog/integrations-core/pull/5036).
* [Added] Add SAP HANA integration. See [#4502](https://github.com/DataDog/integrations-core/pull/4502).
* [Added] Better metadata assertion output. See [#4953](https://github.com/DataDog/integrations-core/pull/4953).
* [Added] Use a stub class for metadata testing. See [#4919](https://github.com/DataDog/integrations-core/pull/4919).
* [Added] Extract version utils and use semver for version comparison. See [#4844](https://github.com/DataDog/integrations-core/pull/4844).
* [Added] Add new version metadata scheme. See [#4929](https://github.com/DataDog/integrations-core/pull/4929).
* [Added] Add total_time_to_temporal_percent utility. See [#4924](https://github.com/DataDog/integrations-core/pull/4924).
* [Added] Standardize logging format. See [#4906](https://github.com/DataDog/integrations-core/pull/4906).
* [Added] Add auth type to RequestsWrapper. See [#4708](https://github.com/DataDog/integrations-core/pull/4708).
* [Fixed] Fix no instances case for AgentCheck signature and add more tests. See [#4784](https://github.com/DataDog/integrations-core/pull/4784).

## 9.5.0 / 2019-10-22

* [Added] Upgrade psycopg2-binary to 2.8.4. See [#4840](https://github.com/DataDog/integrations-core/pull/4840).
* [Added] Add mechanism to submit metadata from OpenMetrics checks. See [#4757](https://github.com/DataDog/integrations-core/pull/4757).
* [Added] Properly fall back to wildcards when defined OpenMetrics transformers do not get a match. See [#4757](https://github.com/DataDog/integrations-core/pull/4757).

## 9.4.2 / 2019-10-17 / Agent 6.15.0

* [Fixed] Fix RequestsWrapper session `timeout`. See [#4811](https://github.com/DataDog/integrations-core/pull/4811).

## 9.4.1 / 2019-10-17

* [Fixed] Avoid sending additional gauges for openmetrics histograms if using distribution metrics. See [#4780](https://github.com/DataDog/integrations-core/pull/4780).

## 9.4.0 / 2019-10-11

* [Added] Add an option to send histograms/summary counts as monotonic counters. See [#4629](https://github.com/DataDog/integrations-core/pull/4629).
* [Added] Add option for device testing in e2e. See [#4693](https://github.com/DataDog/integrations-core/pull/4693).
* [Added] Update self.warning to accept `*args`. See [#4731](https://github.com/DataDog/integrations-core/pull/4731).
* [Added] Send configuration metadata by default. See [#4730](https://github.com/DataDog/integrations-core/pull/4730).
* [Added] Add mechanism to execute setup steps before the first check run. See [#4713](https://github.com/DataDog/integrations-core/pull/4713).
* [Added] Implement Python API for setting check metadata. See [#4686](https://github.com/DataDog/integrations-core/pull/4686).
* [Added] Upgrade Paramiko to version 2.6.0. See [#4685](https://github.com/DataDog/integrations-core/pull/4685). Thanks [daniel-savo](https://github.com/daniel-savo).
* [Added] Add support for fetching consumer offsets stored in Kafka to `monitor_unlisted_consumer_groups`. See [#3957](https://github.com/DataDog/integrations-core/pull/3957). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Support submitting memory profiling metrics during E2E. See [#4635](https://github.com/DataDog/integrations-core/pull/4635).
* [Added] Add a way to submit non-namespaced metrics and service checks. See [#4637](https://github.com/DataDog/integrations-core/pull/4637).
* [Added] Add duplication assertion methods to aggregator stub. See [#4521](https://github.com/DataDog/integrations-core/pull/4521).
* [Added] Add option to override KRB5CCNAME env var. See [#4578](https://github.com/DataDog/integrations-core/pull/4578).
* [Deprecated] Add a deprecated warning message to NetworkCheck. See [#4560](https://github.com/DataDog/integrations-core/pull/4560).
* [Added] Upgrade pywin32 to 225. See [#4563](https://github.com/DataDog/integrations-core/pull/4563).
* [Fixed] Upgrade psutil dependency to 5.6.3. See [#4442](https://github.com/DataDog/integrations-core/pull/4442).

## 9.3.2 / 2019-08-30 / Agent 6.14.0

* [Fixed] Update class signature to support the RequestsWrapper. See [#4469](https://github.com/DataDog/integrations-core/pull/4469).

## 9.3.1 / 2019-08-28

* [Fixed] Fix decumulating bucket on multiple contexts. See [#4446](https://github.com/DataDog/integrations-core/pull/4446).

## 9.3.0 / 2019-08-24

* [Added] Add each checks' unique ID to logs. See [#4410](https://github.com/DataDog/integrations-core/pull/4410).
* [Added] Support continuous memory profiling metric submission. See [#4409](https://github.com/DataDog/integrations-core/pull/4409).
* [Fixed] Remove unused dependencies. See [#4405](https://github.com/DataDog/integrations-core/pull/4405).
* [Added] Upgrade pyasn1. See [#4289](https://github.com/DataDog/integrations-core/pull/4289).
* [Fixed] Fix http invert without explicit default. See [#4277](https://github.com/DataDog/integrations-core/pull/4277).
* [Added] Bump Kazoo to 2.6.1 to pull in some minor bugfixes. See [#4260](https://github.com/DataDog/integrations-core/pull/4260). Thanks [jeffwidman](https://github.com/jeffwidman).
* [Added] Support memory profiling metrics. See [#4239](https://github.com/DataDog/integrations-core/pull/4239).
* [Added] Set timeout from init_config in requests wrapper as default. See [#4226](https://github.com/DataDog/integrations-core/pull/4226).
* [Fixed] Fix prometheus and openmetric unicode labels. See [#4157](https://github.com/DataDog/integrations-core/pull/4157).
* [Added] Add the version of an AgentCheck as a property. See [#4228](https://github.com/DataDog/integrations-core/pull/4228).
* [Added] Upgrade JPype1 to 0.7.0. See [#4211](https://github.com/DataDog/integrations-core/pull/4211).
* [Added] Add option for specifying extra headers in RequestsWrapper. See [#4208](https://github.com/DataDog/integrations-core/pull/4208).
* [Added] Add the ability to debug memory usage. See [#4166](https://github.com/DataDog/integrations-core/pull/4166).
* [Fixed] Fix openmetrics telemetry memory usage in mixins. See [#4193](https://github.com/DataDog/integrations-core/pull/4193).
* [Added] Add tuple timeout format to Request Remapper. See [#4172](https://github.com/DataDog/integrations-core/pull/4172).

## 9.2.1 / 2019-07-19 / Agent 6.13.0

* [Fixed] Fix openmetrics mixins telemetry metrics. See [#4155](https://github.com/DataDog/integrations-core/pull/4155).

## 9.2.0 / 2019-07-19

* [Added] Add telemetry metrics counter by ksm collector. See [#4125](https://github.com/DataDog/integrations-core/pull/4125).

## 9.1.0 / 2019-07-13

* [Added] Telemetry check's metrics. See [#4025](https://github.com/DataDog/integrations-core/pull/4025). Thanks [clamoriniere](https://github.com/clamoriniere).

## 9.0.0 / 2019-07-12

* [Changed] Add SSL support for psycopg2, remove pg8000. See [#4096](https://github.com/DataDog/integrations-core/pull/4096).
* [Added] Upgrade pymongo to 3.8. See [#4095](https://github.com/DataDog/integrations-core/pull/4095).
* [Fixed] Fix label encoding. See [#4073](https://github.com/DataDog/integrations-core/pull/4073) and [#4089](https://github.com/DataDog/integrations-core/pull/4089).

## 8.6.0 / 2019-07-09

* [Added] Output similar metrics on failed aggregator stub assertions to help debugging. See [#4035](https://github.com/DataDog/integrations-core/pull/4035) and [#4076](https://github.com/DataDog/integrations-core/pull/4076).
* [Fixed] Avoid WMISampler inheriting from Thread. See [#4051](https://github.com/DataDog/integrations-core/pull/4051).

## 8.5.0 / 2019-07-04

* [Fixed] Make WMISampler hashable. See [#4043](https://github.com/DataDog/integrations-core/pull/4043).
* [Added] Support SOCKS proxies. See [#4021](https://github.com/DataDog/integrations-core/pull/4021).
* [Added] Update cryptography version. See [#4000](https://github.com/DataDog/integrations-core/pull/4000).
* [Added] Add others forms of auth to RequestsWrapper. See [#3956](https://github.com/DataDog/integrations-core/pull/3956).
* [Fixed] Fix busy loop in WMI implementation. See [#4018](https://github.com/DataDog/integrations-core/pull/4018).
* [Added] Add others forms of auth to RequestsWrapper. See [#3956](https://github.com/DataDog/integrations-core/pull/3956).
* [Added] Better log message for unsafe yaml loading/dumping. See [#3771](https://github.com/DataDog/integrations-core/pull/3771).

## 8.4.1 / 2019-06-29 / Agent 6.12.2

* [Fixed] Change WMISampler class to create a single thread, owned by the object. See [#3987](https://github.com/DataDog/integrations-core/pull/3987).

## 8.4.0 / 2019-06-18

* [Added] Support E2E testing. See [#3896](https://github.com/DataDog/integrations-core/pull/3896).

## 8.3.3 / 2019-06-05 / Agent 6.12.0

* [Fixed] Revert "[openmetrics] allow blacklisting of strings". See [#3867](https://github.com/DataDog/integrations-core/pull/3867).
* [Fixed] Encode hostname in set_external_tags. See [#3866](https://github.com/DataDog/integrations-core/pull/3866).

## 8.3.2 / 2019-06-04

* [Fixed] Revert: Properly utilize the provided `metrics_mapper`. See [#3861](https://github.com/DataDog/integrations-core/pull/3861).

## 8.3.1 / 2019-06-02

* [Fixed] Fix package order of `get_datadog_wheels`. See [#3847](https://github.com/DataDog/integrations-core/pull/3847).

## 8.3.0 / 2019-06-01

* [Added] [openmetrics] Use Kube service account bearer token for authentication. See [#3829](https://github.com/DataDog/integrations-core/pull/3829).
* [Fixed] Add upper_bound tag for the total count when collecting histograms buckets. See [#3777](https://github.com/DataDog/integrations-core/pull/3777).

## 8.2.0 / 2019-05-21

* [Added] Upgrade requests to 2.22.0. See [#3778](https://github.com/DataDog/integrations-core/pull/3778).

## 8.1.0 / 2019-05-14

* [Fixed] Fix the initialization of ignored metrics for OpenMetrics. See [#3736](https://github.com/DataDog/integrations-core/pull/3736).
* [Fixed] Fixed decoding warning for None tags for python2 check base class. See [#3665](https://github.com/DataDog/integrations-core/pull/3665).
* [Added] Add logging support to RequestsWrapper. See [#3737](https://github.com/DataDog/integrations-core/pull/3737).

## 8.0.0 / 2019-05-06

* [Added] Add easier namespacing for data submission. See [#3718](https://github.com/DataDog/integrations-core/pull/3718).
* [Added] Upgrade pyyaml to 5.1. See [#3698](https://github.com/DataDog/integrations-core/pull/3698).
* [Fixed] Improve resiliency of logging initialization phase. See [#3705](https://github.com/DataDog/integrations-core/pull/3705).
* [Added] Upgrade psutil dependency to 5.6.2. See [#3684](https://github.com/DataDog/integrations-core/pull/3684).
* [Changed] Remove every default header except `User-Agent`. See [#3644](https://github.com/DataDog/integrations-core/pull/3644).
* [Fixed] Handle more tag decoding errors. See [#3671](https://github.com/DataDog/integrations-core/pull/3671).
* [Added] Adhere to code style. See [#3496](https://github.com/DataDog/integrations-core/pull/3496).
* [Fixed] Properly utilize the provided `metrics_mapper`. See [#3446](https://github.com/DataDog/integrations-core/pull/3446). Thanks [casidiablo](https://github.com/casidiablo).
* [Added] Upgrade psycopg2-binary to 2.8.2. See [#3649](https://github.com/DataDog/integrations-core/pull/3649).

## 7.0.0 / 2019-04-18

* [Added] Add service_identity dependency. See [#3256](https://github.com/DataDog/integrations-core/pull/3256).
* [Changed] Standardize TLS/SSL protocol naming. See [#3620](https://github.com/DataDog/integrations-core/pull/3620).
* [Fixed] Parse timeouts as floats in RequestsWrapper. See [#3448](https://github.com/DataDog/integrations-core/pull/3448).
* [Added] Support Python 3. See [#3605](https://github.com/DataDog/integrations-core/pull/3605).

## 6.6.1 / 2019-04-04 / Agent 6.11.0

* [Fixed] Don't ship `pyodbc` on macOS as SQLServer integration is not shipped on macOS. See [#3461](https://github.com/DataDog/integrations-core/pull/3461).

## 6.6.0 / 2019-03-29

* [Added] Upgrade in-toto. See [#3411](https://github.com/DataDog/integrations-core/pull/3411).
* [Added] Support Python 3. See [#3425](https://github.com/DataDog/integrations-core/pull/3425).

## 6.5.0 / 2019-03-29

* [Added] Add tagging utility and stub to access the new tagger API. See [#3413](https://github.com/DataDog/integrations-core/pull/3413).

## 6.4.0 / 2019-03-22

* [Added] Add external_host_tags wrapper to checks_base. See [#3316](https://github.com/DataDog/integrations-core/pull/3316).
* [Added] Add ability to debug checks with pdb. See [#2690](https://github.com/DataDog/integrations-core/pull/2690).
* [Added] Add a wrapper for requests. See [#3310](https://github.com/DataDog/integrations-core/pull/3310).
* [Fixed] Ensure the use of relative imports to avoid circular dependencies. See [#3326](https://github.com/DataDog/integrations-core/pull/3326).
* [Fixed] Remove uuid dependency. See [#3309](https://github.com/DataDog/integrations-core/pull/3309).
* [Fixed] Properly ship flup on Python 3. See [#3304](https://github.com/DataDog/integrations-core/pull/3304).

## 6.3.0 / 2019-03-14

* [Added] Add rfc3339 utilities. See [#3189](https://github.com/DataDog/integrations-core/pull/3189).
* [Added] Backport Agent V6 utils to the AgentCheck class. See [#3261](https://github.com/DataDog/integrations-core/pull/3261).

## 6.2.0 / 2019-03-10

* [Added] Upgrade protobuf to 3.7.0. See [#3272](https://github.com/DataDog/integrations-core/pull/3272).
* [Added] Upgrade requests to 2.21.0. See [#3274](https://github.com/DataDog/integrations-core/pull/3274).
* [Added] Upgrade six to 1.12.0. See [#3276](https://github.com/DataDog/integrations-core/pull/3276).
* [Added] Add iter_unique util. See [#3269](https://github.com/DataDog/integrations-core/pull/3269).
* [Fixed] Fixed decoding warning for None tags. See [#3249](https://github.com/DataDog/integrations-core/pull/3249).
* [Added] Upgrade aerospike dependency. See [#3235](https://github.com/DataDog/integrations-core/pull/3235).
* [Fixed] ensure_unicode with normalize for py3 compatibility. See [#3218](https://github.com/DataDog/integrations-core/pull/3218).

## 6.1.0 / 2019-02-20

* [Added] Add openstacksdk option to openstack_controller. See [#3109](https://github.com/DataDog/integrations-core/pull/3109).

## 6.0.1 / 2019-02-20 / Agent 6.10.0

* [Fixed] Import kubernetes lazily to reduce memory footprint. See [#3166](https://github.com/DataDog/integrations-core/pull/3166).

## 6.0.0 / 2019-02-12

* [Added] Expose the single check instance as an attribute. See [#3093](https://github.com/DataDog/integrations-core/pull/3093).
* [Added] Parse raw yaml instances and init_config with dedicated base class method. See [#3098](https://github.com/DataDog/integrations-core/pull/3098).
* [Added] Add datadog-checks-downloader. See [#3026](https://github.com/DataDog/integrations-core/pull/3026).
* [Fixed] Resolve flake8 issues. See [#3060](https://github.com/DataDog/integrations-core/pull/3060).
* [Fixed] Properly prevent critical logs during testing. See [#3053](https://github.com/DataDog/integrations-core/pull/3053).
* [Changed] Fix riakcs dependencies. See [#3033](https://github.com/DataDog/integrations-core/pull/3033).
* [Added] Support Python 3 Base WMI. See [#3036](https://github.com/DataDog/integrations-core/pull/3036).
* [Added] Upgrade psutil. See [#3019](https://github.com/DataDog/integrations-core/pull/3019).
* [Fixed] Remove extra log about error encoding tag. See [#2976](https://github.com/DataDog/integrations-core/pull/2976).
* [Added] Support Python 3. See [#2835](https://github.com/DataDog/integrations-core/pull/2835).
* [Fixed] Improve log messages for when tags aren't utf-8. See [#2966](https://github.com/DataDog/integrations-core/pull/2966).

## 5.2.0 / 2019-01-16

* [Added] Make service check statuses available as constants. See [#2960][1].

## 5.1.0 / 2019-01-15

* [Fixed] Always ensure_unicode for subprocess output. See [#2941][2].
* [Added] Add round method to checks base. See [#2931][3].
* [Added] Added lxml dependency. See [#2846][4].
* [Fixed] Include count as an aggregate type in tests. See [#2920][5].
* [Added] Support unicode for Python 3 bindings. See [#2869][6].

## 5.0.1 / 2019-01-07 / Agent 6.9.0

* [Fixed] Fix context limit logic for OpenMetrics checks. See [#2877][7].

## 5.0.0 / 2019-01-04

* [Added] Add kube_controller_manager integration. See [#2845][8].
* [Added] Add kube_leader mixin to monitor leader elections. See [#2796][9].
* [Fixed] Use 'format()' function to create device tag. See [#2822][10].
* [Added] Prevent caching of PDH counter instances by default. See [#2654][11].
* [Added] Prevent critical logs during testing. See [#2840][12].
* [Added] Support trace logging. See [#2838][13].
* [Fixed] Bump pyodbc for python3.7 compatibility. See [#2801][14].
* [Added] Bump psycopg2-binary version to 2.7.5. See [#2799][15].
* [Fixed] Fix metric normalization function for Python 3. See [#2784][16].
* [Added] Support Python 3. See [#2780][17].
* [Changed] Bump kafka-python and kazoo. See [#2766][18].
* [Added] Support Python 3. See [#2738][19].

## 4.6.0 / 2018-12-07 / Agent 6.8.0

* [Added] Fix unicode handling of log messages. See [#2698][20].
* [Fixed] Ensure unicode for subprocess output. See [#2697][21].

## 4.5.0 / 2018-12-02

* [Added] Improve OpenMetrics label joins. See [#2624][22].

## 4.4.0 / 2018-11-30

* [Added] Add linux as supported OS. See [#2614][23].
* [Added] Upgrade cryptography. See [#2659][24].
* [Added] Upgrade requests. See [#2656][25].
* [Fixed] Fix not_asserted aggregator stub function. See [#2639][26].
* [Added] Log line where `AgentCheck.warning` was called in the check. See [#2620][27].
* [Fixed] Fix requirements-agent-release.txt updating. See [#2617][28].

## 4.3.0 / 2018-11-12

* [Added] Add option to prevent subprocess command logging. See [#2565][29].
* [Added] Support Kerberos auth. See [#2516][30].
* [Added] Add option to send additional metric tags for Open Metrics. See [#2514][31].
* [Added] Add standard ssl_verify option to Open Metrics. See [#2507][32].
* [Added] Winpdh improve exception messages. See [#2486][33].
* [Added] Upgrade requests. See [#2481][34].
* [Fixed] Fix bug making the network check read /proc instead of /host/proc on containers. See [#2460][35].
* [Added] Fix unicode handling on A6. See [#2435][36].

## 4.2.0 / 2018-10-16 / Agent 6.6.0

* [Added] Expose text conversion methods. See [#2420][37].
* [Fixed] Handle unicode strings in non-float handler's error message. See [#2419][38].

## 4.1.0 / 2018-10-12

* [Added] Expose core functionality at the root. See [#2394][39].
* [Added] base: add check name to Limiter warning message. See [#2391][40].
* [Fixed] Fix import of _get_py_loglevel. See [#2383][41].
* [Fixed] Fix hostname override and type for status_report.count metrics. See [#2372][42].

## 4.0.0 / 2018-10-11

* [Added] Added generic error class ConfigurationError. See [#2367][43].
* [Changed] Add base subpackage to datadog_checks_base. See [#2331][44].
* [Added] Freeze Agent requirements. See [#2328][45].
* [Added] Pin pywin32 dependency. See [#2322][46].

## 3.0.0 / 2018-09-25

* [Added] Adds ability to Trace "check" function with DD APM. See [#2079][47].
* [Changed] Catch exception when string sent as metric value. See [#2293][48].
* [Changed] Revert default prometheus metric limit to 2000. See [#2248][49].
* [Fixed] Fix base class imports for Agent 5. See [#2232][50].

## 2.2.1 / 2018-09-11 / Agent 6.5.0

* [Fixed] Temporarily increase the limit of prometheus metrics sent for 6.5. See [#2214][51].

## 2.2.0 / 2018-09-06

* [Changed] Freeze pyVmomi dep in base check. See [#2181][52].

## 2.1.0 / 2018-09-05

* [Changed] Change order of precedence of whitelist and blacklist for pattern filtering. See [#2174][53].

## 2.0.0 / 2018-09-04

* [Added] Add cluster-name suffix to node-names in kubernetes state. See [#2069][54].
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][55].
* [Changed] Allow checks to manually specify in their configuration which defaults to use. See [#2145][56].
* [Fixed] Moves WMI Check to Pytest. See [#2133][57].
* [Changed] Use different defaults if scraper_config is created by OpenMetricsBaseCheck. See [#2135][58].
* [Fixed] Fix Prometheus scraping for Python 3. See [#2128][59].
* [Changed] Drop protobuf support for OpenMetrics. See [#2098][60].
* [Added] Add code coverage. See [#2105][61].
* [Changed] Create OpenMetricsBaseCheck, an improved version of GenericPrometheusCheck. See [#1976][62].
* [Fixed] Move RiakCS to pytest, fixes duped tags in RiakCS, adds google_cloud_engine pip dep. See [#2081][63].

## 1.5.0 / 2018-08-19

* [Added] Allow installation of base dependencies. See [#2067][64].
* [Fixed] Retrieve no_proxy directly from the Datadog Agent's configuration. See [#2004][65].
* [Added] Support Python 3 for datadog_checks_base. See [#1957][66].
* [Fixed] Properly skip proxy environment variables. See [#1935][67].
* [Fixed] Update cryptography to 2.3. See [#1927][68].

## 1.4.0 / 2018-07-18 / Agent 6.4.0

* [Fixed] fix packaging of agent requirements. See [#1911][69].
* [Fixed] Properly use skip_proxy for instance configuration. See [#1880][70].
* [Fixed] Sync WMI utils from dd-agent to datadog-checks-base. See [#1897][71].
* [Fixed] Improve check performance by filtering it's input before parsing. See [#1875][72].
* [Changed] Bump prometheus client library to 0.3.0. See [#1866][73].
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790][74].

## 1.3.2 / 2018-06-15

* [Changed] Bump requests to 2.19.1. See [#1743][75].

## 1.3.1 / 2018-06-13

* [Fixed] upgrade requests dependency. See [#1734][76].
* [Changed] Set requests stream option to false when scraping Prometheus endpoints. See [#1596][77].

## 1.3.0 / 2018-06-07

* [Fixed] change default value of AgentCheck.check_id for Agent 6. See [#1652][78].
* [Added] Support for gathering metrics from prometheus endpoint for the kubelet itself.. See [#1581][79].
* [Added] include wmi for compat. See [#1565][80].
* [Added] added missing tailfile util. See [#1566][81].
* [Fixed] [base] when running A6, mirror logging behavior. See [#1561][82].

## 1.2.2 / 2018-05-11

* [FEATURE] The generic Prometheus check will now send counter as monotonic counter.
* [BUG] Prometheus requests can use an insecure option
* [BUG] Correctly handle missing counters/strings in PDH checks when possible
* [BUG] Fix Prometheus Scrapper logger
* [SANITY] Clean-up export for `PDHBaseCheck` + export `WinPDHCounter`. [#1183][83]
* [IMPROVEMENT] Discard metrics with invalid values

## 1.2.1 / 2018-03-23

* [BUG] Correctly handle internationalized versions of Windows in the PDH library.
* [FEATURE] Keep track of Service Checks in the Aggregator stub.

## 1.1.0 / 2018-03-23

* [FEATURE] Add a generic prometheus check base class & rework prometheus check using a mixin

## 1.0.0 / 2017-03-22

* [FEATURE] adds `datadog_checks`

<!--- The following link definition list is generated by PimpMyChangelog --->
[1]: https://github.com/DataDog/integrations-core/pull/2960
[2]: https://github.com/DataDog/integrations-core/pull/2941
[3]: https://github.com/DataDog/integrations-core/pull/2931
[4]: https://github.com/DataDog/integrations-core/pull/2846
[5]: https://github.com/DataDog/integrations-core/pull/2920
[6]: https://github.com/DataDog/integrations-core/pull/2869
[7]: https://github.com/DataDog/integrations-core/pull/2877
[8]: https://github.com/DataDog/integrations-core/pull/2845
[9]: https://github.com/DataDog/integrations-core/pull/2796
[10]: https://github.com/DataDog/integrations-core/pull/2822
[11]: https://github.com/DataDog/integrations-core/pull/2654
[12]: https://github.com/DataDog/integrations-core/pull/2840
[13]: https://github.com/DataDog/integrations-core/pull/2838
[14]: https://github.com/DataDog/integrations-core/pull/2801
[15]: https://github.com/DataDog/integrations-core/pull/2799
[16]: https://github.com/DataDog/integrations-core/pull/2784
[17]: https://github.com/DataDog/integrations-core/pull/2780
[18]: https://github.com/DataDog/integrations-core/pull/2766
[19]: https://github.com/DataDog/integrations-core/pull/2738
[20]: https://github.com/DataDog/integrations-core/pull/2698
[21]: https://github.com/DataDog/integrations-core/pull/2697
[22]: https://github.com/DataDog/integrations-core/pull/2624
[23]: https://github.com/DataDog/integrations-core/pull/2614
[24]: https://github.com/DataDog/integrations-core/pull/2659
[25]: https://github.com/DataDog/integrations-core/pull/2656
[26]: https://github.com/DataDog/integrations-core/pull/2639
[27]: https://github.com/DataDog/integrations-core/pull/2620
[28]: https://github.com/DataDog/integrations-core/pull/2617
[29]: https://github.com/DataDog/integrations-core/pull/2565
[30]: https://github.com/DataDog/integrations-core/pull/2516
[31]: https://github.com/DataDog/integrations-core/pull/2514
[32]: https://github.com/DataDog/integrations-core/pull/2507
[33]: https://github.com/DataDog/integrations-core/pull/2486
[34]: https://github.com/DataDog/integrations-core/pull/2481
[35]: https://github.com/DataDog/integrations-core/pull/2460
[36]: https://github.com/DataDog/integrations-core/pull/2435
[37]: https://github.com/DataDog/integrations-core/pull/2420
[38]: https://github.com/DataDog/integrations-core/pull/2419
[39]: https://github.com/DataDog/integrations-core/pull/2394
[40]: https://github.com/DataDog/integrations-core/pull/2391
[41]: https://github.com/DataDog/integrations-core/pull/2383
[42]: https://github.com/DataDog/integrations-core/pull/2372
[43]: https://github.com/DataDog/integrations-core/pull/2367
[44]: https://github.com/DataDog/integrations-core/pull/2331
[45]: https://github.com/DataDog/integrations-core/pull/2328
[46]: https://github.com/DataDog/integrations-core/pull/2322
[47]: https://github.com/DataDog/integrations-core/pull/2079
[48]: https://github.com/DataDog/integrations-core/pull/2293
[49]: https://github.com/DataDog/integrations-core/pull/2248
[50]: https://github.com/DataDog/integrations-core/pull/2232
[51]: https://github.com/DataDog/integrations-core/pull/2214
[52]: https://github.com/DataDog/integrations-core/pull/2181
[53]: https://github.com/DataDog/integrations-core/pull/2174
[54]: https://github.com/DataDog/integrations-core/pull/2069
[55]: https://github.com/DataDog/integrations-core/pull/2093
[56]: https://github.com/DataDog/integrations-core/pull/2145
[57]: https://github.com/DataDog/integrations-core/pull/2133
[58]: https://github.com/DataDog/integrations-core/pull/2135
[59]: https://github.com/DataDog/integrations-core/pull/2128
[60]: https://github.com/DataDog/integrations-core/pull/2098
[61]: https://github.com/DataDog/integrations-core/pull/2105
[62]: https://github.com/DataDog/integrations-core/pull/1976
[63]: https://github.com/DataDog/integrations-core/pull/2081
[64]: https://github.com/DataDog/integrations-core/pull/2067
[65]: https://github.com/DataDog/integrations-core/pull/2004
[66]: https://github.com/DataDog/integrations-core/pull/1957
[67]: https://github.com/DataDog/integrations-core/pull/1935
[68]: https://github.com/DataDog/integrations-core/pull/1927
[69]: https://github.com/DataDog/integrations-core/pull/1911
[70]: https://github.com/DataDog/integrations-core/pull/1880
[71]: https://github.com/DataDog/integrations-core/pull/1897
[72]: https://github.com/DataDog/integrations-core/pull/1875
[73]: https://github.com/DataDog/integrations-core/pull/1866
[74]: https://github.com/DataDog/integrations-core/pull/1790
[75]: https://github.com/DataDog/integrations-core/pull/1743
[76]: https://github.com/DataDog/integrations-core/pull/1734
[77]: https://github.com/DataDog/integrations-core/pull/1596
[78]: https://github.com/DataDog/integrations-core/pull/1652
[79]: https://github.com/DataDog/integrations-core/pull/1581
[80]: https://github.com/DataDog/integrations-core/pull/1565
[81]: https://github.com/DataDog/integrations-core/pull/1566
[82]: https://github.com/DataDog/integrations-core/pull/1561
[83]: https://github.com/DataDog/integrations-core/issues/1183
