# CHANGELOG - docker_daemon

<!-- towncrier release notes start -->

## 1.12.0 / 2020-01-13

***Added***:

* Use lazy logging format ([#5398](https://github.com/DataDog/integrations-core/pull/5398))
* Use lazy logging format ([#5377](https://github.com/DataDog/integrations-core/pull/5377))

## 1.11.0 / 2019-05-14

***Added***:

* Support docker.kmem.usage ([#3339](https://github.com/DataDog/integrations-core/pull/3339)) Thanks [wolf31o2](https://github.com/wolf31o2).

## 1.10.2 / 2019-01-04

***Fixed***:

* Demote critical log levels to error ([#2795](https://github.com/DataDog/integrations-core/pull/2795))

## 1.10.1 / 2018-09-04

***Fixed***:

* Add data files to the wheel package ([#1727](https://github.com/DataDog/integrations-core/pull/1727))
* Log debug, not warning, for missing /proc/net/dev files ([#1583](https://github.com/DataDog/integrations-core/pull/1583)) Thanks [lachlancooper](https://github.com/lachlancooper).

## 1.10.0 / 2018-05-11

***Added***:

* Add docker.cpu.shares metric. See [#1358]()

## 1.9.0 / 2018-03-23

***Added***:

* add the new `exec_die` event type to default exclusion list. See [#1240]()

## 1.8.0 / 2018-02-13

***Added***:

* Add `short_image` tag to container metrics. See [#986]()

## 1.7.0 / 2018-01-10

***Added***:

* Honor global collect_labels_as_tags if integration's collect_labels_as_tags is empty. See [#881]()
* Improve logging when cgroup metrics can't be retrieved. See [#914]()

## 1.6.0 / 2017-11-21

***Added***:

* Add custom tags to all service checks ([#782](https://github)com/DataDog/integrations-core/issues/782)
* Add docker memory soft limit metric ([#760](https://github)com/DataDog/integrations-core/issues/760)
* Add docker.containers.running.total & docker.containers.stopped.total metrics ([#859](https://github)com/DataDog/integrations-core/issues/859)

## 1.5.1 / 2017-11-08

***Fixed***:

* Fix lost kubernetes tags in 1.5.0 ([#817](https://github)com/DataDog/integrations-core/issues/817)

## 1.5.0 / 2017-10-10

***Added***:

* Remove namespace from pod_name tag ([#770](https://github)com/DataDog/integrations-core/issues/770)

## 1.4.0 / 2017-09-12

***Added***:

* Add an option to wait for docker if it's not ready at start time ([#722](https://github)com/DataDog/integrations-core/issues/722)
* Add client-side event filtering by event type ([#744](https://github)com/DataDog/integrations-core/issues/744)

## 1.3.2 / 2017-08-28

***Added***:

* Add "image_name:openshift/origin-pod" to suggested exclude list ([#641](https://github)com/DataDog/integrations-core/issues/641)

***Fixed***:

* safely check volume list before accessing ([#544](https://github)com/DataDog/integrations-core/issues/544)
* make it a bit safer ([#701](https://github)com/DataDog/integrations-core/issues/701)

## 1.3.1 / 2017-07-26

***Fixed***:

* fix event collection on ecs and nomad ([#616](https://github)com/DataDog/integrations-core/issues/616)

## 1.3.0 / 2017-07-18

***Added***:

* collect kube_container_name by default in docker_daemon check, like kubernetes does ([#553](https://github)com/DataDog/integrations-core/issues/553)
* add kube_container_name tag to kubernetes and docker integrations ([#509](https://github.com/DataDog/integrations-core/issues/509), thanks [@sophaskins](https://github)com/sophaskins)
* remove NomadUtil & ECSUtil from docker_daemon, MetadataCollector proxies them ([#486](https://github)com/DataDog/integrations-core/issues/486)
* use the new orchestrator.Tagger class to retrieve the Mesos tags for docker metrics ([#466](https://github)com/DataDog/integrations-core/issues/466)

## 1.2.0 / 2017-06-05

***Added***:

* Add option to extract docker event attibutes as tags ([#404](https://github)com/DataDog/integrations-core/issues/404)
* Add option to cap rate values to filter out cgroup CPU spikes ([#412](https://github)com/DataDog/integrations-core/issues/412)
* Tag metrics with Nomad task/group/job names when available ([#305](https://github)com/DataDog/integrations-core/issues/305)
* Support the new diskmapper statsd format for docker.disk.* metrics ([#409](https://github)com/DataDog/integrations-core/issues/409)
* Report a service check when the Docker daemon is unreachable ([#354](https://github)com/DataDog/integrations-core/issues/354)
* Add docker.cpu.usage metric for global container CPU usage ([#385](https://github)com/DataDog/integrations-core/issues/385)

***Fixed***:

* Docker events are tagged with the image name when docker reports its checksum ([#415](https://github)com/DataDog/integrations-core/issues/415)

## 1.1.1 / 2017-05-11

***Fixed***:

* catch IOError exception when container exits in the middle of a check run ([#408](https://github)com/DataDog/integrations-core/issues/408)
* fix image name when using sha256 for specs ([#393](https://github)com/DataDog/integrations-core/issues/393)

## 1.1.0 / 2017-04-24

***Added***:

* reduce network mapping logging output ([#348](https://github)com/DataDog/integrations-core/issues/348)
* Kubernetes: catch kubeutil init exception ([#345](https://github)com/DataDog/integrations-core/issues/345)
* kubernetes 1.6+ cgroups hierarchy support ([#333](https://github)com/DataDog/integrations-core/issues/333)
* ECS handle NetworkMode:host ([#320](https://github)com/DataDog/integrations-core/issues/320)
* adds docker_network tagging to `docker.net.bytes_*` metrics, needs dd-agent >= 5.13.0 ([#277](https://github)com/DataDog/integrations-core/issues/277)
* adds the ability to monitor for docker exits failure with service check `docker.exit` ([#290](https://github)com/DataDog/integrations-core/issues/290)
* collect rancher label container name as tag ([#282](https://github)com/DataDog/integrations-core/issues/282)

## 1.0.0 / 2017-03-22

***Added***:

* adds docker_daemon integration.
