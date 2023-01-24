# CHANGELOG - Kube_proxy

## 6.0.1 / 2023-01-20

* [Fixed] Fix setting of default health URL for kube_dns, kube_proxy, kube_metrics_server health checks. See [#13571](https://github.com/DataDog/integrations-core/pull/13571).

## 6.0.0 / 2022-12-09 / Agent 7.42.0

* [Changed] Add health check to kube_* integrations. See [#10668](https://github.com/DataDog/integrations-core/pull/10668).

## 5.3.0 / 2022-09-16 / Agent 7.40.0

* [Added] Update HTTP config spec templates. See [#12890](https://github.com/DataDog/integrations-core/pull/12890).

## 5.2.0 / 2022-05-15 / Agent 7.37.0

* [Added] Support dynamic bearer tokens (Bound Service Account Token Volume). See [#11915](https://github.com/DataDog/integrations-core/pull/11915).

## 5.1.0 / 2022-04-05 / Agent 7.36.0

* [Added] Add metric_patterns options to filter all metric submission by a list of regexes. See [#11695](https://github.com/DataDog/integrations-core/pull/11695).
* [Fixed] Remove outdated warning in the description for the `tls_ignore_warning` option. See [#11591](https://github.com/DataDog/integrations-core/pull/11591).

## 5.0.0 / 2022-02-19 / Agent 7.35.0

* [Added] Add `pyproject.toml` file. See [#11384](https://github.com/DataDog/integrations-core/pull/11384).
* [Fixed] Fix namespace packaging on Python 2. See [#11532](https://github.com/DataDog/integrations-core/pull/11532).
* [Changed] Add tls_protocols_allowed option documentation. See [#11251](https://github.com/DataDog/integrations-core/pull/11251).

## 4.0.2 / 2022-01-21 / Agent 7.34.0

* [Fixed] Remove new kube proxy metric with high cardinality. See [#11182](https://github.com/DataDog/integrations-core/pull/11182).

## 4.0.1 / 2022-01-18

* [Fixed] Fix the type of `bearer_token_auth`. See [#11144](https://github.com/DataDog/integrations-core/pull/11144).

## 4.0.0 / 2022-01-08

* [Changed] Improve kube_proxy metrics. See [#11052](https://github.com/DataDog/integrations-core/pull/11052).

## 3.5.0 / 2021-11-13 / Agent 7.33.0

* [Added] Document new include_labels option. See [#10617](https://github.com/DataDog/integrations-core/pull/10617).
* [Added] Document new use_process_start_time option. See [#10601](https://github.com/DataDog/integrations-core/pull/10601).
* [Added] Add kube_proxy config spec. See [#10510](https://github.com/DataDog/integrations-core/pull/10510).

## 3.4.1 / 2021-03-07 / Agent 7.27.0

* [Fixed] Bump minimum base package version. See [#8443](https://github.com/DataDog/integrations-core/pull/8443).

## 3.4.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 3.3.1 / 2020-04-04 / Agent 7.19.0

* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).

## 3.3.0 / 2020-01-13 / Agent 7.17.0

* [Added] Make OpenMetrics use the RequestsWrapper. See [#5414](https://github.com/DataDog/integrations-core/pull/5414).

## 3.2.0 / 2019-05-14 / Agent 6.12.0

* [Added] Adhere to code style. See [#3529](https://github.com/DataDog/integrations-core/pull/3529).

## 3.1.0 / 2019-02-18 / Agent 6.10.0

* [Added] Support Python 3. See [#2919](https://github.com/DataDog/integrations-core/pull/2919).

## 3.0.0 / 2018-10-12 / Agent 6.6.0

* [Changed] Update kube_proxy to use the new OpenMetricsBaseCheck. See [#1981][1].

## 2.0.0 / 2018-09-04 / Agent 6.5.0

* [Added] Limit Prometheus/OpenMetrics checks to 2000 metrics per run by default. See [#2093][2].
* [Fixed] Make sure all checks' versions are exposed. See [#1945][3].
* [Added] Make HTTP request timeout configurable in prometheus checks. See [#1790][4].
* [Changed] Removing unnecessary and misleading kube_proxy auto_conf.yaml. See [#1792][5].
* [Fixed] Add data files to the wheel package. See [#1727][6].

## 1.1.0 / 2018-06-07

* [Added] Package `auto_conf.yaml` for appropriate integrations. See [#1664][7].

## 1.0.0/ 2018-03-23

* [FEATURE] adds kube_proxy integration.
[1]: https://github.com/DataDog/integrations-core/pull/1981
[2]: https://github.com/DataDog/integrations-core/pull/2093
[3]: https://github.com/DataDog/integrations-core/pull/1945
[4]: https://github.com/DataDog/integrations-core/pull/1790
[5]: https://github.com/DataDog/integrations-core/pull/1792
[6]: https://github.com/DataDog/integrations-core/pull/1727
[7]: https://github.com/DataDog/integrations-core/pull/1664
