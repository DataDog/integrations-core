# CHANGELOG - kubelet

1.2.0 / Unreleased
==================

### Changes

* [FEATURE] Collect metrics directly from cadvisor, for kubenetes version older than 1.7.6. See [#1339][]
* [FEATURE] Add instance tags to all metrics. Improve the coverage of the check. See [#1377][]
* [BUGFIX] Reports nanocores instead of cores. See [#1361][]
* [FEATURE] Allow to disable prometheus metric collection. See [#1423][]
* [FEATURE] Container metrics now respect the container filtering rules. Requires Agent 6.2+. See [#1442][]
* [BUGFIX] Fix submission of CPU metrics on multi-threaded containers. See [#1489][]
* [BUGFIX] Fix SSL when using the insecure options but still providing certificates

1.1.0 / 2018-03-23
==================

### Changes

* [FEATURE] Support TLS


1.0.0 / 2018-02-28
==================


### Changes

* [FEATURE] add kubelet integration.

