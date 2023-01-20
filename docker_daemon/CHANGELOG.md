# CHANGELOG - docker_daemon

## 1.12.0 / 2020-01-13

* [Added] Use lazy logging format. See [#5398](https://github.com/DataDog/integrations-core/pull/5398).
* [Added] Use lazy logging format. See [#5377](https://github.com/DataDog/integrations-core/pull/5377).

## 1.11.0 / 2019-05-14

* [Added] Support docker.kmem.usage. See [#3339](https://github.com/DataDog/integrations-core/pull/3339). Thanks [wolf31o2](https://github.com/wolf31o2).

## 1.10.2 / 2019-01-04

* [Fixed] Demote critical log levels to error. See [#2795](https://github.com/DataDog/integrations-core/pull/2795).

## 1.10.1 / 2018-09-04

* [Fixed] Add data files to the wheel package. See [#1727](https://github.com/DataDog/integrations-core/pull/1727).
* [Fixed] Log debug, not warning, for missing /proc/net/dev files. See [#1583](https://github.com/DataDog/integrations-core/pull/1583). Thanks [lachlancooper](https://github.com/lachlancooper).

## 1.10.0 / 2018-05-11

* [IMPROVEMENT] Add docker.cpu.shares metric. See [#1358]()

## 1.9.0 / 2018-03-23

* [IMPROVEMENT] add the new `exec_die` event type to default exclusion list. See [#1240]()

## 1.8.0 / 2018-02-13

* [IMPROVEMENT] Add `short_image` tag to container metrics. See [#986]()

## 1.7.0 / 2018-01-10

* [FEATURE] Honor global collect_labels_as_tags if integration's collect_labels_as_tags is empty. See [#881]()
* [IMPROVEMENT] Improve logging when cgroup metrics can't be retrieved. See [#914]()

## 1.6.0 / 2017-11-21

* [IMPROVEMENT] Add custom tags to all service checks. See [#782](https://github.com/DataDog/integrations-core/issues/782)
* [IMPROVEMENT] Add docker memory soft limit metric. See [#760](https://github.com/DataDog/integrations-core/issues/760)
* [IMPROVEMENT] Add docker.containers.running.total & docker.containers.stopped.total metrics. See [#859](https://github.com/DataDog/integrations-core/issues/859)

## 1.5.1 / 2017-11-08

* [BUGFIX] Fix lost kubernetes tags in 1.5.0. See [#817](https://github.com/DataDog/integrations-core/issues/817)

## 1.5.0 / 2017-10-10

* [IMPROVEMENT] Remove namespace from pod_name tag. See [#770](https://github.com/DataDog/integrations-core/issues/770)

## 1.4.0 / 2017-09-12

* [FEATURE] Add an option to wait for docker if it's not ready at start time. See [#722](https://github.com/DataDog/integrations-core/issues/722)
* [FEATURE] Add client-side event filtering by event type. See [#744](https://github.com/DataDog/integrations-core/issues/744)

## 1.3.2 / 2017-08-28

* [IMPROVEMENT] Add "image_name:openshift/origin-pod" to suggested exclude list. See [#641](https://github.com/DataDog/integrations-core/issues/641)
* [BUGFIX] safely check volume list before accessing. See [#544](https://github.com/DataDog/integrations-core/issues/544)
* [BUGFIX] make it a bit safer. See [#701](https://github.com/DataDog/integrations-core/issues/701)

## 1.3.1 / 2017-07-26

* [BUGFIX] fix event collection on ecs and nomad. See [#616](https://github.com/DataDog/integrations-core/issues/616)

## 1.3.0 / 2017-07-18

* [FEATURE] collect kube_container_name by default in docker_daemon check, like kubernetes does. See [#553](https://github.com/DataDog/integrations-core/issues/553)
* [FEATURE] add kube_container_name tag to kubernetes and docker integrations. See [#509](https://github.com/DataDog/integrations-core/issues/509), thanks [@sophaskins](https://github.com/sophaskins)
* [IMPROVEMENT] remove NomadUtil & ECSUtil from docker_daemon, MetadataCollector proxies them. See [#486](https://github.com/DataDog/integrations-core/issues/486)
* [IMPROVEMENT] use the new orchestrator.Tagger class to retrieve the Mesos tags for docker metrics. See [#466](https://github.com/DataDog/integrations-core/issues/466)

## 1.2.0 / 2017-06-05

* [FEATURE] Add option to extract docker event attibutes as tags. See [#404](https://github.com/DataDog/integrations-core/issues/404)
* [FEATURE] Add option to cap rate values to filter out cgroup CPU spikes. See [#412](https://github.com/DataDog/integrations-core/issues/412)
* [IMPROVEMENT] Tag metrics with Nomad task/group/job names when available. See [#305](https://github.com/DataDog/integrations-core/issues/305)
* [IMPROVEMENT] Support the new diskmapper statsd format for docker.disk.* metrics. See [#409](https://github.com/DataDog/integrations-core/issues/409)
* [IMPROVEMENT] Report a service check when the Docker daemon is unreachable. See [#354](https://github.com/DataDog/integrations-core/issues/354)
* [IMPROVEMENT] Add docker.cpu.usage metric for global container CPU usage. See [#385](https://github.com/DataDog/integrations-core/issues/385)
* [BUGFIX] Docker events are tagged with the image name when docker reports its checksum. See [#415](https://github.com/DataDog/integrations-core/issues/415)

## 1.1.1 / 2017-05-11

* [BUGFIX] catch IOError exception when container exits in the middle of a check run. See [#408](https://github.com/DataDog/integrations-core/issues/408)
* [BUGFIX] fix image name when using sha256 for specs. See [#393](https://github.com/DataDog/integrations-core/issues/393)

## 1.1.0 / 2017-04-24

* [FEATURE] reduce network mapping logging output. See [#348](https://github.com/DataDog/integrations-core/issues/348)
* [FEATURE] Kubernetes: catch kubeutil init exception. See [#345](https://github.com/DataDog/integrations-core/issues/345)
* [FEATURE] kubernetes 1.6+ cgroups hierarchy support. See [#333](https://github.com/DataDog/integrations-core/issues/333)
* [FEATURE] ECS handle NetworkMode:host. See [#320](https://github.com/DataDog/integrations-core/issues/320)
* [FEATURE] adds docker_network tagging to `docker.net.bytes_*` metrics, needs dd-agent >= 5.13.0. See [#277](https://github.com/DataDog/integrations-core/issues/277)
* [FEATURE] adds the ability to monitor for docker exits failure with service check `docker.exit`. See [#290](https://github.com/DataDog/integrations-core/issues/290)
* [FEATURE] collect rancher label container name as tag. See [#282](https://github.com/DataDog/integrations-core/issues/282)

## 1.0.0 / 2017-03-22

* [FEATURE] adds docker_daemon integration.
