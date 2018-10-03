# CHANGELOG - datadog_checks_base

## 3.0.0 / 2018-09-25

* [Added] Adds ability to Trace "check" function with DD APM. See [#2079](https://github.com/DataDog/integrations-core/pull/2079).
* [Changed] Catch exception when string sent as metric value. See [#2293](https://github.com/DataDog/integrations-core/pull/2293).
* [Changed] Revert default prometheus metric limit to 2000. See [#2248](https://github.com/DataDog/integrations-core/pull/2248).
* [Fixed] Fix base class imports for Agent 5. See [#2232](https://github.com/DataDog/integrations-core/pull/2232).

## 2.2.1 / 2018-09-11

* [Fixed] Temporarily increase the limit of prometheus metrics sent for 6.5. See [#2214](https://github.com/DataDog/integrations-core/pull/2214).

## 2.2.0 / 2018-09-06

* [Changed] Freeze pyVmomi dep in base check. See [#2181](https://github.com/DataDog/integrations-core/pull/2181).

## 2.1.0 / 2018-09-05

* [Changed] Change order of precedence of whitelist and blacklist for pattern filtering. See [#2174](https://github.com/DataDog/integrations-core/pull/2174).

## 2.0.0 / 2018-09-04

* [Added] Add cluster-name suffix to node-names in kubernetes state. See [#2069](https://github.com/DataDog/integrations-core/pull/2069).
* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093](https://github.com/DataDog/integrations-core/pull/2093).
* [Changed] Allow checks to manually specify in their configuration which defaults to use. See [#2145](https://github.com/DataDog/integrations-core/pull/2145).
* [Fixed] Moves WMI Check to Pytest. See [#2133](https://github.com/DataDog/integrations-core/pull/2133).
* [Changed] Use different defaults if scraper_config is created by OpenMetricsBaseCheck. See [#2135](https://github.com/DataDog/integrations-core/pull/2135).
* [Fixed] Fix Prometheus scraping for Python 3. See [#2128](https://github.com/DataDog/integrations-core/pull/2128).
* [Changed] Drop protobuf support for OpenMetrics. See [#2098](https://github.com/DataDog/integrations-core/pull/2098).
* [Added] Add code coverage. See [#2105](https://github.com/DataDog/integrations-core/pull/2105).
* [Changed] Create OpenMetricsBaseCheck, an improved version of GenericPrometheusCheck. See [#1976](https://github.com/DataDog/integrations-core/pull/1976).
* [Fixed] Move RiakCS to pytest, fixes duped tags in RiakCS, adds google_cloud_engine pip dep. See [#2081](https://github.com/DataDog/integrations-core/pull/2081).

## 1.5.0 / 2018-08-19

* [Added] Allow installation of base dependencies. See [#2067](https://github.com/DataDog/integrations-core/pull/2067).
* [Fixed] Retrieve no_proxy directly from the Datadog Agent's configuration. See [#2004](https://github.com/DataDog/integrations-core/pull/2004).
* [Added] Support Python 3 for datadog_checks_base. See [#1957](https://github.com/DataDog/integrations-core/pull/1957).
* [Fixed] Properly skip proxy environment variables. See [#1935](https://github.com/DataDog/integrations-core/pull/1935).
* [Fixed] Update cryptography to 2.3. See [#1927](https://github.com/DataDog/integrations-core/pull/1927).

## 1.4.0 / 2018-07-18

* [Fixed] fix packaging of agent requirements. See [#1911](https://github.com/DataDog/integrations-core/pull/1911).
* [Fixed] Properly use skip_proxy for instance configuration. See [#1880](https://github.com/DataDog/integrations-core/pull/1880).
* [Fixed] Sync WMI utils from dd-agent to datadog-checks-base. See [#1897](https://github.com/DataDog/integrations-core/pull/1897).
* [Fixed] Improve check performance by filtering it's input before parsing. See [#1875](https://github.com/DataDog/integrations-core/pull/1875).
* [Changed] Bump prometheus client library to 0.3.0. See [#1866](https://github.com/DataDog/integrations-core/pull/1866).
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790](https://github.com/DataDog/integrations-core/pull/1790).

## 1.3.2 / 2018-06-15

* [Changed] Bump requests to 2.19.1. See [#1743](https://github.com/DataDog/integrations-core/pull/1743).

## 1.3.1 / 2018-06-13

* [Fixed] upgrade requests dependency. See [#1734](https://github.com/DataDog/integrations-core/pull/1734).
* [Changed] Set requests stream option to false when scraping Prometheus endpoints. See [#1596](https://github.com/DataDog/integrations-core/pull/1596).

## 1.3.0 / 2018-06-07

* [Fixed] change default value of AgentCheck.check_id for Agent 6. See [#1652](https://github.com/DataDog/integrations-core/pull/1652).
* [Added] Support for gathering metrics from prometheus endpoint for the kubelet itself.. See [#1581](https://github.com/DataDog/integrations-core/pull/1581).
* [Added] include wmi for compat. See [#1565](https://github.com/DataDog/integrations-core/pull/1565).
* [Added] added missing tailfile util. See [#1566](https://github.com/DataDog/integrations-core/pull/1566).
* [Fixed] [base] when running A6, mirror logging behavior. See [#1561](https://github.com/DataDog/integrations-core/pull/1561).

## 1.2.2 / 2018-05-11

* [FEATURE] The generic Prometheus check will now send counter as monotonic counter.
* [BUG] Prometheus requests can use an insecure option
* [BUG] Correctly handle missing counters/strings in PDH checks when possible
* [BUG] Fix Prometheus Scrapper logger
* [SANITY] Clean-up export for `PDHBaseCheck` + export `WinPDHCounter`. [#1183][]
* [IMPROVEMENT] Discard metrics with invalid values

## 1.2.1 / 2018-03-23

* [BUG] Correctly handle internationalized versions of Windows in the PDH library.
* [FEATURE] Keep track of Service Checks in the Aggregator stub.

## 1.1.0 / 2018-03-23

* [FEATURE] Add a generic prometheus check base class & rework prometheus check using a mixin

## 1.0.0 / 2017-03-22

* [FEATURE] adds `datadog_checks`

<!--- The following link definition list is generated by PimpMyChangelog --->
[#1183]: https://github.com/DataDog/integrations-core/issues/1183
