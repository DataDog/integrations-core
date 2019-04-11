# CHANGELOG - IBM MQ
## 2.0.0 / 2019-04-12

* [Removed] host from config file
* [Added] mq_host to config file. This replaces previous host to avoid collision with agent host tag

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
