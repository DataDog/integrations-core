# CHANGELOG - IBM MQ

## 3.1.1 / 2019-07-29

* [Fixed] Fix ibm_mq e2e import issue. See [#4140](https://github.com/DataDog/integrations-core/pull/4140).

## 3.1.0 / 2019-07-04

* [Fixed] Use MQCMD_INQUIRE_Q instead of queue.inquire. See [#3997](https://github.com/DataDog/integrations-core/pull/3997).
* [Added] Add ibm_mq.channel.count metric and ibm_mq.channel.status service check. See [#3958](https://github.com/DataDog/integrations-core/pull/3958).

## 3.0.0 / 2019-06-20

* [Changed] [ibm_mq] fix queue auto discovery to include any type in addition to qmodel and included regex matching on queue names. See [#3893](https://github.com/DataDog/integrations-core/pull/3893).

## 2.0.0 / 2019-04-16

* [Changed] Breaking change: Change host tag for mq_host. Dashboards and monitors may be affected. See [#3608](https://github.com/DataDog/integrations-core/pull/3608).
* [Added] Adhere to code style. See [#3519](https://github.com/DataDog/integrations-core/pull/3519).
* [Fixed] fix queue_manager variable naming of IBM MQ. See [#3592](https://github.com/DataDog/integrations-core/pull/3592).

## 1.2.0 / 2019-03-29

* [Added] Add ability to add additional tags to queues matching a regex. See [#3399](https://github.com/DataDog/integrations-core/pull/3399).
* [Added] adds channel metrics. See [#3360](https://github.com/DataDog/integrations-core/pull/3360).
* [Fixed] fix ssl variable naming for IBM MQ. See [#3312](https://github.com/DataDog/integrations-core/pull/3312).

## 1.1.0 / 2019-02-18

* [Added] Autodiscover queues. See [#3061](https://github.com/DataDog/integrations-core/pull/3061).

## 1.0.1 / 2019-01-04

* [Fixed] Fix Oldest Message Age. See [#2859][1].

## 1.0.0 / 2018-12-09

* [Added] IBM MQ Integration. See [#2154][2].

[1]: https://github.com/DataDog/integrations-core/pull/2859
[2]: https://github.com/DataDog/integrations-core/pull/2154
