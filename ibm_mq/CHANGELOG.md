# CHANGELOG - IBM MQ

## 3.11.1 / 2021-01-25

* [Fixed] Better explain ssl_key_repository_location. See [#8417](https://github.com/DataDog/integrations-core/pull/8417).

## 3.11.0 / 2020-11-19 / Agent 7.25.0

* [Added] Add new queue stats metrics for IBM MQ. See [#8032](https://github.com/DataDog/integrations-core/pull/8032).

## 3.10.0 / 2020-10-31 / Agent 7.24.0

* [Added] [doc] Add encoding in log config sample. See [#7708](https://github.com/DataDog/integrations-core/pull/7708).

## 3.9.0 / 2020-09-21 / Agent 7.23.0

* [Added] Support Certificate Label and login/password for SSL conf. See [#7202](https://github.com/DataDog/integrations-core/pull/7202).
* [Fixed] Raise exception on connection error. See [#7563](https://github.com/DataDog/integrations-core/pull/7563).

## 3.8.2 / 2020-09-10

* [Fixed] Try normal connection before SSL connection. See [#7554](https://github.com/DataDog/integrations-core/pull/7554).
* [Fixed] Improve error reporting when pymqi is not installed. See [#7048](https://github.com/DataDog/integrations-core/pull/7048).
* [Fixed] Fix style for the latest release of Black. See [#7438](https://github.com/DataDog/integrations-core/pull/7438).

## 3.8.1 / 2020-08-10 / Agent 7.22.0

* [Fixed] Update logs config service field to optional. See [#7209](https://github.com/DataDog/integrations-core/pull/7209).

## 3.8.0 / 2020-07-23

* [Added] IBM MQ metadata. See [#6979](https://github.com/DataDog/integrations-core/pull/6979).
* [Added] Collect metrics from Statistics Messages. See [#6945](https://github.com/DataDog/integrations-core/pull/6945).
* [Fixed] Avoid shadowing depth_percent function. See [#7132](https://github.com/DataDog/integrations-core/pull/7132).

## 3.7.0 / 2020-06-29 / Agent 7.21.0

* [Added] Add MacOS Support. See [#6927](https://github.com/DataDog/integrations-core/pull/6927).
* [Fixed] Refactor to make encoding more consistent. See [#6995](https://github.com/DataDog/integrations-core/pull/6995).
* [Fixed] Ensure bytes for ssl connection. See [#6913](https://github.com/DataDog/integrations-core/pull/6913).
* [Fixed] Fix template specs typos. See [#6912](https://github.com/DataDog/integrations-core/pull/6912).
* [Fixed] Move metrics collection logic to separate files. See [#6752](https://github.com/DataDog/integrations-core/pull/6752).

## 3.6.0 / 2020-05-17 / Agent 7.20.0

* [Added] Allow optional dependency installation for all checks. See [#6589](https://github.com/DataDog/integrations-core/pull/6589).

## 3.5.1 / 2020-04-08 / Agent 7.19.0

* [Fixed] Don't import pymqi unconditionally. See [#6286](https://github.com/DataDog/integrations-core/pull/6286).

## 3.5.0 / 2020-04-04

* [Added] Apply config specs to IBM MQ. See [#5903](https://github.com/DataDog/integrations-core/pull/5903).
* [Fixed] Update deprecated imports. See [#6088](https://github.com/DataDog/integrations-core/pull/6088).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).

## 3.4.0 / 2020-03-11

* [Added] Add `connection_name` configuration. See [#6015](https://github.com/DataDog/integrations-core/pull/6015).
* [Added] Add configuration option for the Channel Definition API version. See [#5905](https://github.com/DataDog/integrations-core/pull/5905).
* [Added] Upgrade pymqi to 1.10.1. See [#5955](https://github.com/DataDog/integrations-core/pull/5955).
* [Fixed] IBM MQ refactor. See [#5902](https://github.com/DataDog/integrations-core/pull/5902).

## 3.3.1 / 2020-01-17 / Agent 7.17.0

* [Fixed] Fix metric type and missing metrics in metadata.csv. See [#5470](https://github.com/DataDog/integrations-core/pull/5470).

## 3.3.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).
* [Added] Add channel metrics. See [#5116](https://github.com/DataDog/integrations-core/pull/5116).

## 3.2.1 / 2019-09-18 / Agent 6.15.0

* [Fixed] Improve IBM MQ docs and logging. See [#4540](https://github.com/DataDog/integrations-core/pull/4540).
* [Fixed] Fix duplicate service checks. See [#4525](https://github.com/DataDog/integrations-core/pull/4525).

## 3.2.0 / 2019-08-21 / Agent 6.14.0

* [Added] Add channel_status_mapping config. See [#4395](https://github.com/DataDog/integrations-core/pull/4395).

## 3.1.1 / 2019-07-29

* [Fixed] Fix ibm_mq e2e import issue. See [#4140](https://github.com/DataDog/integrations-core/pull/4140).

## 3.1.0 / 2019-07-04 / Agent 6.13.0

* [Fixed] Use MQCMD_INQUIRE_Q instead of queue.inquire. See [#3997](https://github.com/DataDog/integrations-core/pull/3997).
* [Added] Add ibm_mq.channel.count metric and ibm_mq.channel.status service check. See [#3958](https://github.com/DataDog/integrations-core/pull/3958).

## 3.0.0 / 2019-06-20

* [Changed] [ibm_mq] fix queue auto discovery to include any type in addition to qmodel and included regex matching on queue names. See [#3893](https://github.com/DataDog/integrations-core/pull/3893).

## 2.0.0 / 2019-04-16 / Agent 6.12.0

* [Changed] Breaking change: Change host tag for mq_host. Dashboards and monitors may be affected. See [#3608](https://github.com/DataDog/integrations-core/pull/3608).
* [Added] Adhere to code style. See [#3519](https://github.com/DataDog/integrations-core/pull/3519).
* [Fixed] fix queue_manager variable naming of IBM MQ. See [#3592](https://github.com/DataDog/integrations-core/pull/3592).

## 1.2.0 / 2019-03-29 / Agent 6.11.0

* [Added] Add ability to add additional tags to queues matching a regex. See [#3399](https://github.com/DataDog/integrations-core/pull/3399).
* [Added] adds channel metrics. See [#3360](https://github.com/DataDog/integrations-core/pull/3360).
* [Fixed] fix ssl variable naming for IBM MQ. See [#3312](https://github.com/DataDog/integrations-core/pull/3312).

## 1.1.0 / 2019-02-18 / Agent 6.10.0

* [Added] Autodiscover queues. See [#3061](https://github.com/DataDog/integrations-core/pull/3061).

## 1.0.1 / 2019-01-04 / Agent 6.9.0

* [Fixed] Fix Oldest Message Age. See [#2859][1].

## 1.0.0 / 2018-12-09 / Agent 6.8.0

* [Added] IBM MQ Integration. See [#2154][2].

[1]: https://github.com/DataDog/integrations-core/pull/2859
[2]: https://github.com/DataDog/integrations-core/pull/2154
