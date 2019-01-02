# CHANGELOG - Datadog Checks Dev

## 0.16.0 / 2018-12-22

* [Added] Remove requirements.txt from check template. See [#2816](https://github.com/DataDog/integrations-core/pull/2816).
* [Added] Add ability to log warnings during pytest. See [#2764](https://github.com/DataDog/integrations-core/pull/2764).
* [Fixed] Fix agent_changelog command. See [#2808](https://github.com/DataDog/integrations-core/pull/2808).
* [Added] Update templates for new integrations. See [#2794](https://github.com/DataDog/integrations-core/pull/2794).
* [Added] Add python3 compatibility validation. See [#2736](https://github.com/DataDog/integrations-core/pull/2736).
* [Added] Validate checks dependencies against the embedded environment. See [#2746](https://github.com/DataDog/integrations-core/pull/2746).
* [Added] Add constant to check if platform is Linux. See [#2782](https://github.com/DataDog/integrations-core/pull/2782).
* [Fixed] Do not consider empty string as a version change. See [#2771](https://github.com/DataDog/integrations-core/pull/2771).
* [Changed] Rename `ddev release freeze` to `ddev release agent_req_file`, refactor commands code. See [#2765](https://github.com/DataDog/integrations-core/pull/2765).
* [Added] Add validation for configuration files. See [#2759](https://github.com/DataDog/integrations-core/pull/2759).
* [Added] Add ability to pass state to e2e tear down. See [#2724](https://github.com/DataDog/integrations-core/pull/2724).
* [Added] Add ability to use dev version of base package for e2e. See [#2689](https://github.com/DataDog/integrations-core/pull/2689).

## 0.15.1 / 2018-11-30

* [Fixed] Handle unreleased checks for agent reqs validation. See [#2664](https://github.com/DataDog/integrations-core/pull/2664).

## 0.15.0 / 2018-11-27

* [Added] Added Watt units to metadata validation. See [#2645](https://github.com/DataDog/integrations-core/pull/2645).
* [Added] Added Heap and Volume units to metadata validation. See [#2647](https://github.com/DataDog/integrations-core/pull/2647).
* [Fixed] Gently handle Yubikey exceptions. See [#2641](https://github.com/DataDog/integrations-core/pull/2641).
* [Added] Added validation step for the agent-requirements file. See [#2642](https://github.com/DataDog/integrations-core/pull/2642).

## 0.14.1 / 2018-11-22

* [Fixed] Increase gpg timeout to give time to developers to interact with Yubikeys. See [#2613](https://github.com/DataDog/integrations-core/pull/2613).
* [Fixed] Fix requirements-agent-release.txt updating. See [#2617](https://github.com/DataDog/integrations-core/pull/2617).

## 0.14.0 / 2018-11-16

* [Added] Support agent repo. See [#2600](https://github.com/DataDog/integrations-core/pull/2600).
* [Added] Improve trello releasing. See [#2599](https://github.com/DataDog/integrations-core/pull/2599).
* [Added] Refactor validations under `validate` command. See [#2593](https://github.com/DataDog/integrations-core/pull/2593).
* [Added] Upgrade docker-compose and requests. See [#2503](https://github.com/DataDog/integrations-core/pull/2503).
* [Added] Disable pytest output capturing when debugging. See [#2502](https://github.com/DataDog/integrations-core/pull/2502).
* [Added] Support specifying type of semver version bumps. See [#2491](https://github.com/DataDog/integrations-core/pull/2491).
* [Fixed] Fixed off-by-one missing latest release. See [#2478](https://github.com/DataDog/integrations-core/pull/2478).
* [Added] Fix codecov error on appveyor. See [#2474](https://github.com/DataDog/integrations-core/pull/2474).
* [Fixed] Use raw string literals when \ is present. See [#2465](https://github.com/DataDog/integrations-core/pull/2465).
* [Fixed] Improve output of `ddev manifest verify` command. See [#2444](https://github.com/DataDog/integrations-core/pull/2444).
* [Added] Add service_checks.json files validation. See [#2432](https://github.com/DataDog/integrations-core/pull/2432).
* [Added] Make all tox envs available to E2E. See [#2457](https://github.com/DataDog/integrations-core/pull/2457).
* [Added] Ensure new checks include the E2E fixture. See [#2455](https://github.com/DataDog/integrations-core/pull/2455).
* [Fixed] Handle any clipboard errors for E2E. See [#2454](https://github.com/DataDog/integrations-core/pull/2454).
* [Added] Prevent misconfigured tox files. See [#2447](https://github.com/DataDog/integrations-core/pull/2447).
* [Fixed] Add `datadog-` prefix to packages name. See [#2430](https://github.com/DataDog/integrations-core/pull/2430).

## 0.13.0 / 2018-10-17

* [Added] Ensure new checks use editable install of datadog_checks_base for tests. See [#2427](https://github.com/DataDog/integrations-core/pull/2427).
* [Fixed] Relax e2e config parsing. See [#2416](https://github.com/DataDog/integrations-core/pull/2416).
* [Fixed] Fix sleep on WaitFor helper. See [#2418](https://github.com/DataDog/integrations-core/pull/2418).

## 0.12.1 / 2018-10-15

* [Fixed] Improve handling of github api errors for trello. See [#2411](https://github.com/DataDog/integrations-core/pull/2411).
* [Fixed] Make every check's `tests` directory path unique for coverage. See [#2406](https://github.com/DataDog/integrations-core/pull/2406).

## 0.12.0 / 2018-10-15

* [Fixed] Fix trello for issue number in commit message. See [#2408](https://github.com/DataDog/integrations-core/pull/2408).
* [Added] Support the initial release of integrations. See [#2399](https://github.com/DataDog/integrations-core/pull/2399).

## 0.11.0 / 2018-10-11

* [Added] Add E2E support. See [#2375](https://github.com/DataDog/integrations-core/pull/2375).
* [Added] Ensure new core checks use latest dev package for testing. See [#2386](https://github.com/DataDog/integrations-core/pull/2386).
* [Fixed] Normalize line endings for release signing. See [#2364](https://github.com/DataDog/integrations-core/pull/2364).
* [Added] Support more teams for Trello test cards. See [#2365](https://github.com/DataDog/integrations-core/pull/2365).

## 0.10.0 / 2018-10-04

* [Added] Update base package paths. See [#2345](https://github.com/DataDog/integrations-core/pull/2345).
* [Added] Add generic environment runner. See [#2342](https://github.com/DataDog/integrations-core/pull/2342).
* [Added] Add WaitFor environment condition. See [#2343](https://github.com/DataDog/integrations-core/pull/2343).
* [Added] Enable pytest plugin to control environments. See [#2336](https://github.com/DataDog/integrations-core/pull/2336).

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
