# CHANGELOG - Datadog Checks Dev

## 0.9.0 / 2018-09-30

* [Added] Allow testing of specific environments. See [#2312](https://github.com/DataDog/integrations-core/pull/2312).
* [Added] Add run command. See [#2319](https://github.com/DataDog/integrations-core/pull/2319).
* [Fixed] Fix namespace overwriting. See [#2311](https://github.com/DataDog/integrations-core/pull/2311).
* [Fixed] Upgrade in-toto to gain full cross-platform release signing support. See [#2315](https://github.com/DataDog/integrations-core/pull/2315).
* [Added] Command to validate metadata. See [#2269](https://github.com/DataDog/integrations-core/pull/2269).

## 0.8.1 / 2018-09-25

* [Fixed] Fix Python 2 unicode handling for log pattern error message. See [#2303](https://github.com/DataDog/integrations-core/pull/2303).

## 0.8.0 / 2018-09-25

* [Added] Add new templates for other integration types. See [#2285](https://github.com/DataDog/integrations-core/pull/2285).
* [Added] Add release signing via in-toto. See [#2224](https://github.com/DataDog/integrations-core/pull/2224).
* [Added] Add prometheus metadata.csv and metric map auto-generation. See [#2117](https://github.com/DataDog/integrations-core/pull/2117).
* [Added] Keep track of the checks changed at every Datadog Agent release. See [#2277](https://github.com/DataDog/integrations-core/pull/2277).

## 0.7.0 / 2018-09-18

* [Added] Fix manifest validation policy. See [#2258](https://github.com/DataDog/integrations-core/pull/2258).
* [Added] Add config option to select the default repository. See [#2243](https://github.com/DataDog/integrations-core/pull/2243).

## 0.6.2 / 2018-09-14

* [Fixed] Revert "Update base package paths (#2235)". See [#2240](https://github.com/DataDog/integrations-core/pull/2240).

## 0.6.1 / 2018-09-14

* [Fixed] Move datadog_checks_base code into sub base package. See [#2167](https://github.com/DataDog/integrations-core/pull/2167).

## 0.6.0 / 2018-09-14

* [Added] Update base package paths. See [#2235](https://github.com/DataDog/integrations-core/pull/2235).
* [Added] Add ability to add wait time in docker_run. See [#2196](https://github.com/DataDog/integrations-core/pull/2196).
* [Added] Add better debugging to test command. See [#2194](https://github.com/DataDog/integrations-core/pull/2194).
* [Fixed] Gracefully handle tags that already exist. See [#2172](https://github.com/DataDog/integrations-core/pull/2172).
* [Fixed] Fix release freeze command. See [#2188](https://github.com/DataDog/integrations-core/pull/2188).
* [Added] Add ability to filter checks to test by changes. See [#2163](https://github.com/DataDog/integrations-core/pull/2163).

## 0.5.0 / 2018-09-04

* [Added] Allow automated releasing by looking at github labels. See [#2169](https://github.com/DataDog/integrations-core/pull/2169).
* [Fixed] Handle character limit for Trello card descriptions. See [#2162](https://github.com/DataDog/integrations-core/pull/2162).

## 0.4.1 / 2018-08-31

* [Fixed] Fix trello command for other repos. See [#2155](https://github.com/DataDog/integrations-core/pull/2155).

## 0.4.0 / 2018-08-28

* [Added] Add code coverage. See [#2105](https://github.com/DataDog/integrations-core/pull/2105).
* [Added] Add command to create new integrations. See [#2037](https://github.com/DataDog/integrations-core/pull/2037).

## 0.3.1 / 2018-08-03

* [Fixed] Fix clean command. See [#1992](https://github.com/DataDog/integrations-core/pull/1992).

## 0.3.0 / 2018-07-30

* [Added] Allow passing --build to compose up. See [#1962](https://github.com/DataDog/integrations-core/pull/1962).
* [Fixed] When setting repo paths do not resolve home. See [#1953](https://github.com/DataDog/integrations-core/pull/1953).
* [Added] Add command to create Trello test cards from Agent release diffs. See [#1934](https://github.com/DataDog/integrations-core/pull/1934).
* [Added] Add openldap to the list of agent integrations. See [#1923](https://github.com/DataDog/integrations-core/pull/1923).
* [Added] Update dep tooling to support environment markers. See [#1921](https://github.com/DataDog/integrations-core/pull/1921).

## 0.2.2 / 2018-07-19

* [Fixed] Relax condition error handling to allow more time. See [#1914](https://github.com/DataDog/integrations-core/pull/1914).
* [Fixed] Do not skip release builds. See [#1913](https://github.com/DataDog/integrations-core/pull/1913).
* [Fixed] Fix packaging of agent requirements. See [#1911](https://github.com/DataDog/integrations-core/pull/1911).

## 0.2.1 / 2018-07-17

* [Fixed] make remove_path util more resilient to errors. See [#1900](https://github.com/DataDog/integrations-core/pull/1900).

## 0.2.0 / 2018-07-17

* [Added] improve docker tooling. See [#1891](https://github.com/DataDog/integrations-core/pull/1891).

## 0.1.1 / 2018-07-12

* [Fixed] fix changed-only test logic. See [#1878](https://github.com/DataDog/integrations-core/pull/1878).

## 0.1.0 / 2018-07-12

* [Added] Add developer package. See [#1862](https://github.com/DataDog/integrations-core/pull/1862).
