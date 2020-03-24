# CHANGELOG - Datadog Checks Dev

## 3.2.0 / 2020-03-24

* [Added] Use Trello for QA release script. See [#6125](https://github.com/DataDog/integrations-core/pull/6125).
* [Added] Add script to resolve username from email. See [#6099](https://github.com/DataDog/integrations-core/pull/6099).
* [Added] Add validation to catch legacy imports. See [#6081](https://github.com/DataDog/integrations-core/pull/6081).
* [Added] Upgrade and pin mypy to 0.770. See [#6090](https://github.com/DataDog/integrations-core/pull/6090).
* [Added] Add config spec option for compact YAML representations of nested arrays. See [#6082](https://github.com/DataDog/integrations-core/pull/6082).
* [Added] Order changelog entries by type. See [#5995](https://github.com/DataDog/integrations-core/pull/5995).
* [Added] Upgrade virtualenv to 20.0.8. See [#5980](https://github.com/DataDog/integrations-core/pull/5980).
* [Added] Add config spec templates for JMX integrations. See [#5978](https://github.com/DataDog/integrations-core/pull/5978).
* [Added] Add meta command to fetch JMX info. See [#5652](https://github.com/DataDog/integrations-core/pull/5652).
* [Added] Add `validate metadata` option to check for more duplicates. See [#5803](https://github.com/DataDog/integrations-core/pull/5803).
* [Added] Add markdown output support to catalog tool. See [#5946](https://github.com/DataDog/integrations-core/pull/5946).
* [Added] Bump `datadog-checks-base` version in new integration template. See [#5858](https://github.com/DataDog/integrations-core/pull/5858).
* [Added] Add config spec support for logs-only integrations. See [#5932](https://github.com/DataDog/integrations-core/pull/5932).
* [Fixed] Remove logs sourcecategory. See [#6121](https://github.com/DataDog/integrations-core/pull/6121).
* [Fixed] Remove reference to check in logs-only template. See [#6106](https://github.com/DataDog/integrations-core/pull/6106).
* [Fixed] Fix pathing issues with CI setup script. See [#6100](https://github.com/DataDog/integrations-core/pull/6100).
* [Fixed] Bump classifiers. See [#6083](https://github.com/DataDog/integrations-core/pull/6083).
* [Fixed] Make aggregator stub support multiple jmx instances. See [#5966](https://github.com/DataDog/integrations-core/pull/5966).

## 3.1.0 / 2020-03-02

* [Added] Handle logs only integrations for legacy config validator. See [#5900](https://github.com/DataDog/integrations-core/pull/5900).
* [Fixed] Pin virtualenv to 20.0.5. See [#5891](https://github.com/DataDog/integrations-core/pull/5891).
* [Added] Allow excluding specific checks when performing bulk releases. See [#5878](https://github.com/DataDog/integrations-core/pull/5878).
* [Fixed] Fix E2E parsing of JMX collector output. See [#5849](https://github.com/DataDog/integrations-core/pull/5849).

## 3.0.0 / 2020-02-22

* [Fixed] Fix error when scrubbing non-org secrets. See [#5827](https://github.com/DataDog/integrations-core/pull/5827).
* [Changed] Switch to comparing between arbitrary tags/release branches to `ddev release testable`. See [#5556](https://github.com/DataDog/integrations-core/pull/5556).
* [Added] Add `service` option to default configuration. See [#5805](https://github.com/DataDog/integrations-core/pull/5805).
* [Added] Add ability for config templates to reference other templates. See [#5804](https://github.com/DataDog/integrations-core/pull/5804).
* [Added] Better error messages on config specs errors. See [#5763](https://github.com/DataDog/integrations-core/pull/5763).
* [Added] Add an option to skip environment creation for tests. See [#5760](https://github.com/DataDog/integrations-core/pull/5760).
* [Added] Create an integration catalog command in ddev. See [#5660](https://github.com/DataDog/integrations-core/pull/5660).
* [Added] Add tag_prefix argument to the changelog command. See [#5741](https://github.com/DataDog/integrations-core/pull/5741).
* [Fixed] Switch to Python 3.8 in check integration template. See [#5717](https://github.com/DataDog/integrations-core/pull/5717).
* [Fixed] Switch to Agent 6+ signature in check integration test. See [#5718](https://github.com/DataDog/integrations-core/pull/5718).
* [Added] Add type checking to integration check template. See [#5711](https://github.com/DataDog/integrations-core/pull/5711).
* [Added] Refactor root initialization to common utils. See [#5705](https://github.com/DataDog/integrations-core/pull/5705).
* [Added] Add `agent_requirements.in` to non testable files. See [#5693](https://github.com/DataDog/integrations-core/pull/5693).
* [Added] Add git dep support to dep validation cmd. See [#5692](https://github.com/DataDog/integrations-core/pull/5692).
* [Added] Add support for tab completion to CLI. See [#5674](https://github.com/DataDog/integrations-core/pull/5674).
* [Added] Upgrade virtualenv dependency to 20.x. See [#5680](https://github.com/DataDog/integrations-core/pull/5680).

## 2.4.0 / 2020-02-05

* [Added] Upgrade coverage dependency. See [#5647](https://github.com/DataDog/integrations-core/pull/5647).

## 2.3.0 / 2020-02-05

* [Added] Move CI setup script to ddev. See [#5651](https://github.com/DataDog/integrations-core/pull/5651).
* [Added] Add `internal` to repo choices. See [#5649](https://github.com/DataDog/integrations-core/pull/5649).
* [Added] Move remaining flake8 config to .flake8. See [#5635](https://github.com/DataDog/integrations-core/pull/5635).

## 2.2.0 / 2020-02-04

* [Added] Ignore `__path__` for type hinting of all integrations. See [#5639](https://github.com/DataDog/integrations-core/pull/5639).
* [Added] Modify QA release script to create Jira issues instead of Trello cards. See [#5457](https://github.com/DataDog/integrations-core/pull/5457).
* [Added] Add script to remove all labels from an issue or pull request. See [#5636](https://github.com/DataDog/integrations-core/pull/5636).
* [Added] Always pass PROGRAM* to tox. See [#5631](https://github.com/DataDog/integrations-core/pull/5631).
* [Added] Add meta command to upgrade the Python version of all test environments. See [#5616](https://github.com/DataDog/integrations-core/pull/5616).
* [Added] Use the latest beta release of virtualenv for performance improvements. See [#5617](https://github.com/DataDog/integrations-core/pull/5617).
* [Added] Add type checking support to Tox plugin. See [#5595](https://github.com/DataDog/integrations-core/pull/5595).
* [Added] Update `validate agent-reqs` cmd to list unreleased checks. See [#5610](https://github.com/DataDog/integrations-core/pull/5610).
* [Added] Allow specifying `release changelog` output file. See [#5608](https://github.com/DataDog/integrations-core/pull/5608).
* [Added] Allow --help for `run` command. See [#5602](https://github.com/DataDog/integrations-core/pull/5602).
* [Fixed] Stop mounting the docker socket to allow jmx tests to pass. See [#5601](https://github.com/DataDog/integrations-core/pull/5601).
* [Added] Update in-toto and its deps. See [#5599](https://github.com/DataDog/integrations-core/pull/5599).

## 2.1.0 / 2020-01-30

* [Added] Support CI validation for internal repo. See [#5567](https://github.com/DataDog/integrations-core/pull/5567).
* [Fixed] Fix metric validation. See [#5581](https://github.com/DataDog/integrations-core/pull/5581).
* [Added] Make new integrations use config specs. See [#5580](https://github.com/DataDog/integrations-core/pull/5580).
* [Added] Add --org-name/-o to `env start`. See [#5458](https://github.com/DataDog/integrations-core/pull/5458).
* [Added] Add some helpful output to ddev env ls command. See [#5576](https://github.com/DataDog/integrations-core/pull/5576).
* [Fixed] Avoid long break in error message. See [#5575](https://github.com/DataDog/integrations-core/pull/5575).
* [Added] Add Networks and Processes teams in ddev trello tool. See [#5560](https://github.com/DataDog/integrations-core/pull/5560).

## 2.0.0 / 2020-01-27

* [Added] Add validation for CI infrastructure configuration. See [#5479](https://github.com/DataDog/integrations-core/pull/5479).
* [Fixed] Add support for in-toto >= 0.4.2. See [#5497](https://github.com/DataDog/integrations-core/pull/5497).
* [Added] Upgrade dependencies. See [#5528](https://github.com/DataDog/integrations-core/pull/5528).
* [Added] Add service check name validator and sync. See [#5501](https://github.com/DataDog/integrations-core/pull/5501).
* [Changed] Remove Python 2 support from CLI. See [#5512](https://github.com/DataDog/integrations-core/pull/5512).
* [Added] Run flake8 after formatting fixes. See [#5492](https://github.com/DataDog/integrations-core/pull/5492).
* [Added] Add meta command to convert metadata.csv files to Markdown tables. See [#5461](https://github.com/DataDog/integrations-core/pull/5461).

## 1.4.0 / 2020-01-13

* [Added] Validate metric names normalization in metadata.csv. See [#5437](https://github.com/DataDog/integrations-core/pull/5437).
* [Fixed] Fix function call for `release testable`. See [#5432](https://github.com/DataDog/integrations-core/pull/5432).

## 1.3.0 / 2020-01-09

* [Added] Add debug option to base ddev command. See [#5386](https://github.com/DataDog/integrations-core/pull/5386).
* [Added] Add meta command to translate MIB names to OIDs in SNMP profiles. See [#5397](https://github.com/DataDog/integrations-core/pull/5397).
* [Added] Update license years in integration templates. See [#5384](https://github.com/DataDog/integrations-core/pull/5384).
* [Fixed] Fix a few style lints to handle Python 2. See [#5389](https://github.com/DataDog/integrations-core/pull/5389).

## 1.2.0 / 2019-12-31

* [Changed] Change `wrapper` arg for environment runners to `wrappers`. See [#5361](https://github.com/DataDog/integrations-core/pull/5361).
* [Added] Add mechanism to cross-mount temporary log files between containers. See [#5346](https://github.com/DataDog/integrations-core/pull/5346).

## 1.1.0 / 2019-12-27

* [Added] Refactor terraform configs. See [#5339](https://github.com/DataDog/integrations-core/pull/5339).
* [Added] Make configuration specs an asset. See [#5337](https://github.com/DataDog/integrations-core/pull/5337).
* [Fixed] Always pass USERNAME to tox. See [#5335](https://github.com/DataDog/integrations-core/pull/5335).
* [Added] Add meta command to export dashboards. See [#5332](https://github.com/DataDog/integrations-core/pull/5332).
* [Added] Make changes and changelog command work with other repos. See [#5331](https://github.com/DataDog/integrations-core/pull/5331).
* [Fixed] Fix agent status with ddev. See [#5293](https://github.com/DataDog/integrations-core/pull/5293).
* [Added] Decrease default verbosity of tracebacks in pytest. See [#5291](https://github.com/DataDog/integrations-core/pull/5291).
* [Added] Add more global utilities the pytest plugin. See [#5283](https://github.com/DataDog/integrations-core/pull/5283).
* [Added] Display Docker Compose logs when test environment fails to start. See [#5258](https://github.com/DataDog/integrations-core/pull/5258).
* [Fixed] Remove command to validate Python 3 compatibility. See [#5246](https://github.com/DataDog/integrations-core/pull/5246).
* [Added] Implement configuration specifications. See [#5072](https://github.com/DataDog/integrations-core/pull/5072).
* [Fixed] Pin coverage to 4.5.4. See [#5224](https://github.com/DataDog/integrations-core/pull/5224).
* [Added] Add support for switching between multiple orgs' API/APP keys. See [#5197](https://github.com/DataDog/integrations-core/pull/5197).

## 1.0.1 / 2019-12-06

* [Fixed] Fix a bug where we accidentally recorded git-ignored files in in-toto. See [#5129](https://github.com/DataDog/integrations-core/pull/5129).

## 1.0.0 / 2019-12-02

* [Added] Support downloading universal and pure Python wheels. See [#4981](https://github.com/DataDog/integrations-core/pull/4981).
* [Added] Support more metric types for `ddev meta prom`. See [#5071](https://github.com/DataDog/integrations-core/pull/5071).
* [Added] Improve prompts in `ddev clean`. See [#5061](https://github.com/DataDog/integrations-core/pull/5061).
* [Added] Add command to navigate to config directory. See [#5054](https://github.com/DataDog/integrations-core/pull/5054).
* [Changed] Remove logos folder from template. See [#4988](https://github.com/DataDog/integrations-core/pull/4988).
* [Fixed] Handle formatting edge cases for `meta changes`. See [#4970](https://github.com/DataDog/integrations-core/pull/4970).
* [Changed] Remove logo validation. See [#4964](https://github.com/DataDog/integrations-core/pull/4964).
* [Added] Use a stub class for metadata testing. See [#4919](https://github.com/DataDog/integrations-core/pull/4919).
* [Fixed] Never sign an empty release. See [#4933](https://github.com/DataDog/integrations-core/pull/4933).
* [Fixed] Update requirements when updating check. See [#4895](https://github.com/DataDog/integrations-core/pull/4895).
* [Added] Add saved_views metadata field to integration templates. See [#4584](https://github.com/DataDog/integrations-core/pull/4584).

## 0.39.0 / 2019-10-25

* [Added] Add junit option to `ddev env e2e` command. See [#4879](https://github.com/DataDog/integrations-core/pull/4879).
* [Fixed] Change the team label map for Trello card creation. See [#4852](https://github.com/DataDog/integrations-core/pull/4852).
* [Fixed] Update metadata link in template. See [#4869](https://github.com/DataDog/integrations-core/pull/4869).

## 0.38.3 / 2019-10-17

* [Fixed] Fix CHANGELOG.md template to make it work with `ddev release changelog`. See [#4808](https://github.com/DataDog/integrations-core/pull/4808).

## 0.38.2 / 2019-10-17

* [Fixed] Handle the case of pylint returning empty output. See [#4801](https://github.com/DataDog/integrations-core/pull/4801).

## 0.38.1 / 2019-10-15

* [Fixed] Fix ddev testable command to properly use the tag, fallback on the branch if absent. See [#4775](https://github.com/DataDog/integrations-core/pull/4775).

## 0.38.0 / 2019-10-11

* [Added] Add option for device testing in e2e. See [#4693](https://github.com/DataDog/integrations-core/pull/4693).
* [Fixed] Fix lint flake8-logging-format command. See [#4728](https://github.com/DataDog/integrations-core/pull/4728).
* [Added] Add flake8-logging-format. See [#4711](https://github.com/DataDog/integrations-core/pull/4711).

## 0.37.0 / 2019-10-09

* [Added] Increase default Agent flush timeout. See [#4714](https://github.com/DataDog/integrations-core/pull/4714).
* [Fixed] Remove default version from env test. See [#4718](https://github.com/DataDog/integrations-core/pull/4718).
* [Fixed] Handle other Agent images in E2E. See [#4710](https://github.com/DataDog/integrations-core/pull/4710).

## 0.36.0 / 2019-10-07

* [Added] Update teams in ddev trello tool. See [#4702](https://github.com/DataDog/integrations-core/pull/4702).
* [Added] Add dashboard validation. See [#4694](https://github.com/DataDog/integrations-core/pull/4694).
* [Fixed] Don't use a7. See [#4680](https://github.com/DataDog/integrations-core/pull/4680).

## 0.35.1 / 2019-09-30

* [Fixed] Auto detect changes and run tests when yaml files change. See [#4657](https://github.com/DataDog/integrations-core/pull/4657).

## 0.35.0 / 2019-09-30

* [Added] Support submitting memory profiling metrics during E2E. See [#4635](https://github.com/DataDog/integrations-core/pull/4635).

## 0.34.0 / 2019-09-24

* [Added] Improve RetryError message. See [#4619](https://github.com/DataDog/integrations-core/pull/4619).
* [Added] Reload environments if there are extra startup commands. See [#4614](https://github.com/DataDog/integrations-core/pull/4614).
* [Added] Add warning to create command if name is lowercase. See [#4564](https://github.com/DataDog/integrations-core/pull/4564).

## 0.33.0 / 2019-09-19

* [Fixed] Stop identifying core vs extras from the working directory name. See [#4583](https://github.com/DataDog/integrations-core/pull/4583).
* [Added] Update tooling for Azure Pipelines. See [#4536](https://github.com/DataDog/integrations-core/pull/4536).

## 0.32.0 / 2019-08-24

* [Added] Don't fail e2e on unsupported platforms. See [#4398](https://github.com/DataDog/integrations-core/pull/4398).
* [Added] Add K8S e2e util. See [#4203](https://github.com/DataDog/integrations-core/pull/4203).
* [Added] Add SSH port forward e2e util. See [#4147](https://github.com/DataDog/integrations-core/pull/4147).
* [Added] Deployment environment with Terraform. See [#4039](https://github.com/DataDog/integrations-core/pull/4039).
* [Fixed] Use the new Python 2 / 3 Docker images. See [#4246](https://github.com/DataDog/integrations-core/pull/4246).
* [Fixed] Don't put integer in environment. See [#4234](https://github.com/DataDog/integrations-core/pull/4234).
* [Added] Support Python 3 when calling pip for extra E2E start up commands. See [#4213](https://github.com/DataDog/integrations-core/pull/4213).
* [Added] Make `docker_run` clean up volumes and orphaned containers. See [#4212](https://github.com/DataDog/integrations-core/pull/4212).
* [Fixed] Use utcnow instead of now. See [#4192](https://github.com/DataDog/integrations-core/pull/4192).
* [Added] Allow multiple docker Agents to coexist for E2E by randomly assigning ports. See [#4205](https://github.com/DataDog/integrations-core/pull/4205).
* [Added] Add docker_volumes option to E2E metadata. See [#4178](https://github.com/DataDog/integrations-core/pull/4178).
* [Added] Add env check for jmx integrations. See [#4146](https://github.com/DataDog/integrations-core/pull/4146).

## 0.31.1 / 2019-07-19

* [Fixed] Fix get_current_agent_version sorting in ddev. See [#4113](https://github.com/DataDog/integrations-core/pull/4113).

## 0.31.0 / 2019-07-13

* [Added] Add support for selecting an Agent build via environment. See [#4112](https://github.com/DataDog/integrations-core/pull/4112).
* [Added] Add ways to control the colorization of output. See [#4086](https://github.com/DataDog/integrations-core/pull/4086).
* [Added] Support multiple Python versions for E2E. See [#4075](https://github.com/DataDog/integrations-core/pull/4075).

## 0.30.1 / 2019-07-04

* [Fixed] Fix metadata bootstrap workflow. See [#4047](https://github.com/DataDog/integrations-core/pull/4047).

## 0.30.0 / 2019-07-04

* [Fixed] Update wording on installing extras in ddev create command. See [#4032](https://github.com/DataDog/integrations-core/pull/4032).
* [Added] Remove timeout when stopping containers. See [#3973](https://github.com/DataDog/integrations-core/pull/3973).

## 0.29.0 / 2019-06-24

* [Added] Only sign updated checks. See [#3944](https://github.com/DataDog/integrations-core/pull/3944).

## 0.28.0 / 2019-06-19

* [Added] Print line number on validate metadata. See [#3931](https://github.com/DataDog/integrations-core/pull/3931).

## 0.27.0 / 2019-06-18

* [Fixed] Validate interval in metadata validation. See [#3857](https://github.com/DataDog/integrations-core/pull/3857).
* [Added] Support E2E testing. See [#3896](https://github.com/DataDog/integrations-core/pull/3896).
* [Added] Allow releasing multiple checks at once. See [#3881](https://github.com/DataDog/integrations-core/pull/3881).

## 0.26.1 / 2019-06-05

* [Fixed] Fix JMX template. See [#3879](https://github.com/DataDog/integrations-core/pull/3879).
* [Fixed] Update APM team label. See [#3878](https://github.com/DataDog/integrations-core/pull/3878).
* [Fixed] Fix logic to skip docs PRs for release testing. See [#3877](https://github.com/DataDog/integrations-core/pull/3877).

## 0.26.0 / 2019-06-01

* [Added] Better error message when releasing on the wrong branch. See [#3832](https://github.com/DataDog/integrations-core/pull/3832).

## 0.25.2 / 2019-05-28

* [Fixed] Fix tox plugin. See [#3825](https://github.com/DataDog/integrations-core/pull/3825).

## 0.25.1 / 2019-05-24

* [Fixed] Use safe default when validating manifests. See [#3810](https://github.com/DataDog/integrations-core/pull/3810).

## 0.25.0 / 2019-05-20

* [Added] Move all assets to a dedicated directory. See [#3768](https://github.com/DataDog/integrations-core/pull/3768).
* [Added] Upgrade requests to 2.22.0. See [#3778](https://github.com/DataDog/integrations-core/pull/3778).

## 0.24.0 / 2019-05-14

* [Added] Ambari integration. See [#3670](https://github.com/DataDog/integrations-core/pull/3670).
* [Added] Fail if service check file doesn't exist. See [#3691](https://github.com/DataDog/integrations-core/pull/3691).
* [Added] Add default service check file to new checks templates. See [#3726](https://github.com/DataDog/integrations-core/pull/3726).
* [Added] Adds ddev YAML config validator. See [#3679](https://github.com/DataDog/integrations-core/pull/3679).
* [Added] Upgrade pyyaml to 5.1. See [#3698](https://github.com/DataDog/integrations-core/pull/3698).

## 0.23.2 / 2019-04-30

* [Fixed] Remove spurious debug line. See [#3703](https://github.com/DataDog/integrations-core/pull/3703).

## 0.23.1 / 2019-04-30

* [Fixed] Fix creation of jmx & tile integrations. See [#3701](https://github.com/DataDog/integrations-core/pull/3701).
* [Fixed] Fix template for new integration to use argument as display name. See [#3664](https://github.com/DataDog/integrations-core/pull/3664).

## 0.23.0 / 2019-04-22

* [Added] Add extra type for manifest validation. See [#3662](https://github.com/DataDog/integrations-core/pull/3662).
* [Added] Adhere to code style. See [#3497](https://github.com/DataDog/integrations-core/pull/3497).
* [Removed] Remove `pre` from versioning scheme. See [#3655](https://github.com/DataDog/integrations-core/pull/3655).
* [Fixed] Fix changelog generation for new checks. See [#3634](https://github.com/DataDog/integrations-core/pull/3634).

## 0.22.0 / 2019-04-15

* [Added] Build releases automatically. See [#3364](https://github.com/DataDog/integrations-core/pull/3364).
* [Fixed] Fixed language in template for integration extras readme. See [#3606](https://github.com/DataDog/integrations-core/pull/3606).
* [Added] Add validation on integration_id. See [#3598](https://github.com/DataDog/integrations-core/pull/3598).
* [Added] Add ability to specify extra start-up commands for e2e. See [#3594](https://github.com/DataDog/integrations-core/pull/3594).
* [Added] Add a pytest-args option to ddev test. See [#3596](https://github.com/DataDog/integrations-core/pull/3596).
* [Fixed] Ensure style envs support every platform. See [#3482](https://github.com/DataDog/integrations-core/pull/3482).
* [Added] Add posargs in tox.ini. See [#3313](https://github.com/DataDog/integrations-core/pull/3313).
* [Fixed] Fix breakpoint agent check flag. See [#3447](https://github.com/DataDog/integrations-core/pull/3447).
* [Added] Update version of datadog-checks-base for extras. See [#3433](https://github.com/DataDog/integrations-core/pull/3433).

## 0.21.0 / 2019-03-29

* [Added] Upgrade in-toto. See [#3411](https://github.com/DataDog/integrations-core/pull/3411).

## 0.20.0 / 2019-03-28

* [Added] Remove flake8 from tox.ini template. See [#3358](https://github.com/DataDog/integrations-core/pull/3358).
* [Added] Support all options for the Agent check command. See [#3350](https://github.com/DataDog/integrations-core/pull/3350).
* [Added] Add ability to detect if using JMX based on metadata. See [#3330](https://github.com/DataDog/integrations-core/pull/3330).
* [Fixed] Make the aggregator fixture lazily import the stub. See [#3308](https://github.com/DataDog/integrations-core/pull/3308).
* [Added] Add style checker and formatter. See [#3299](https://github.com/DataDog/integrations-core/pull/3299).
* [Added] Add env var support to E2E containers. See [#3263](https://github.com/DataDog/integrations-core/pull/3263).
* [Added] Enforce new integration_id field. See [#3264](https://github.com/DataDog/integrations-core/pull/3264).
* [Added] Add row length validation. See [#3266](https://github.com/DataDog/integrations-core/pull/3266).
* [Added] Add logo validation. See [#3246](https://github.com/DataDog/integrations-core/pull/3246).
* [Fixed] Fix sdist build command. See [#3252](https://github.com/DataDog/integrations-core/pull/3252).
* [Added] Default to Python 3.7 for new checks. See [#3244](https://github.com/DataDog/integrations-core/pull/3244).

## 0.19.1 / 2019-03-01

* [Fixed] Run upload command in the proper location. See [#3239](https://github.com/DataDog/integrations-core/pull/3239).

## 0.19.0 / 2019-03-01

* [Fixed] Fix agent changelog command. See [#3233](https://github.com/DataDog/integrations-core/pull/3233).
* [Added] Add integration_id to manifest validation. See [#3232](https://github.com/DataDog/integrations-core/pull/3232).
* [Added] Add ability to pass -m & -k to pytest. See [#3163](https://github.com/DataDog/integrations-core/pull/3163).
* [Fixed] Properly detect integration folder for py3 validation. See [#3188](https://github.com/DataDog/integrations-core/pull/3188).
* [Added] Provide a way to update to the new agent build config format. See [#3181](https://github.com/DataDog/integrations-core/pull/3181).
* [Fixed] Properly ship datadog-checks-downloader. See [#3169](https://github.com/DataDog/integrations-core/pull/3169).
* [Added] Support datadog_checks_downloader. See [#3164](https://github.com/DataDog/integrations-core/pull/3164).
* [Added] Add util to load jmx metric configs. See [#3162](https://github.com/DataDog/integrations-core/pull/3162).

## 0.18.0 / 2019-02-18

* [Added] Add util to get the directory of current file. See [#3135](https://github.com/DataDog/integrations-core/pull/3135).
* [Fixed] Update e2e start help text for extras integrations. See [#3133](https://github.com/DataDog/integrations-core/pull/3133).
* [Fixed] Fix e2e package install order. See [#3092](https://github.com/DataDog/integrations-core/pull/3092).
* [Added] Add command to build package wheel. See [#3067](https://github.com/DataDog/integrations-core/pull/3067).
* [Added] Add datadog-checks-downloader. See [#3026](https://github.com/DataDog/integrations-core/pull/3026).
* [Added] Add `local` E2E . See [#3064](https://github.com/DataDog/integrations-core/pull/3064).
* [Added] Add command to show changes based on commit date. See [#3063](https://github.com/DataDog/integrations-core/pull/3063).
* [Added] Add e2e command to restart the agent. See [#3054](https://github.com/DataDog/integrations-core/pull/3054).
* [Added] Upgrade pytest-benchmark. See [#2934](https://github.com/DataDog/integrations-core/pull/2934).
* [Added] Add description length metadata validation. See [#2923](https://github.com/DataDog/integrations-core/pull/2923).
* [Added] Allow uploading of any Datadog python package. See [#2907](https://github.com/DataDog/integrations-core/pull/2907).
* [Added] Upgrade pytest plugins. See [#2884](https://github.com/DataDog/integrations-core/pull/2884).

## 0.17.0 / 2019-01-07

* [Added] Use standalone py3 validation. See [#2854][1].
* [Fixed] Fix root folder name when running 'validate' commands on integrations-extras. See [#2879][2].
* [Fixed] Pin pytest because of a regression in pytest-benchmark. See [#2878][3].

## 0.16.0 / 2018-12-22

* [Added] Remove requirements.txt from check template. See [#2816][4].
* [Added] Add ability to log warnings during pytest. See [#2764][5].
* [Fixed] Fix agent_changelog command. See [#2808][6].
* [Added] Update templates for new integrations. See [#2794][7].
* [Added] Add python3 compatibility validation. See [#2736][8].
* [Added] Validate checks dependencies against the embedded environment. See [#2746][9].
* [Added] Add constant to check if platform is Linux. See [#2782][10].
* [Fixed] Do not consider empty string as a version change. See [#2771][11].
* [Changed] Rename `ddev release freeze` to `ddev release agent_req_file`, refactor commands code. See [#2765][12].
* [Added] Add validation for configuration files. See [#2759][13].
* [Added] Add ability to pass state to e2e tear down. See [#2724][14].
* [Added] Add ability to use dev version of base package for e2e. See [#2689][15].

## 0.15.1 / 2018-11-30

* [Fixed] Handle unreleased checks for agent reqs validation. See [#2664][16].

## 0.15.0 / 2018-11-27

* [Added] Added Watt units to metadata validation. See [#2645][17].
* [Added] Added Heap and Volume units to metadata validation. See [#2647][18].
* [Fixed] Gently handle Yubikey exceptions. See [#2641][19].
* [Added] Added validation step for the agent-requirements file. See [#2642][20].

## 0.14.1 / 2018-11-22

* [Fixed] Increase gpg timeout to give time to developers to interact with Yubikeys. See [#2613][21].
* [Fixed] Fix requirements-agent-release.txt updating. See [#2617][22].

## 0.14.0 / 2018-11-16

* [Added] Support agent repo. See [#2600][23].
* [Added] Improve trello releasing. See [#2599][24].
* [Added] Refactor validations under `validate` command. See [#2593][25].
* [Added] Upgrade docker-compose and requests. See [#2503][26].
* [Added] Disable pytest output capturing when debugging. See [#2502][27].
* [Added] Support specifying type of semver version bumps. See [#2491][28].
* [Fixed] Fixed off-by-one missing latest release. See [#2478][29].
* [Added] Fix codecov error on appveyor. See [#2474][30].
* [Fixed] Use raw string literals when \ is present. See [#2465][31].
* [Fixed] Improve output of `ddev manifest verify` command. See [#2444][32].
* [Added] Add service_checks.json files validation. See [#2432][33].
* [Added] Make all tox envs available to E2E. See [#2457][34].
* [Added] Ensure new checks include the E2E fixture. See [#2455][35].
* [Fixed] Handle any clipboard errors for E2E. See [#2454][36].
* [Added] Prevent misconfigured tox files. See [#2447][37].
* [Fixed] Add `datadog-` prefix to packages name. See [#2430][38].

## 0.13.0 / 2018-10-17

* [Added] Ensure new checks use editable install of datadog_checks_base for tests. See [#2427][39].
* [Fixed] Relax e2e config parsing. See [#2416][40].
* [Fixed] Fix sleep on WaitFor helper. See [#2418][41].

## 0.12.1 / 2018-10-15

* [Fixed] Improve handling of github api errors for trello. See [#2411][42].
* [Fixed] Make every check's `tests` directory path unique for coverage. See [#2406][43].

## 0.12.0 / 2018-10-15

* [Fixed] Fix trello for issue number in commit message. See [#2408][44].
* [Added] Support the initial release of integrations. See [#2399][45].

## 0.11.0 / 2018-10-11

* [Added] Add E2E support. See [#2375][46].
* [Added] Ensure new core checks use latest dev package for testing. See [#2386][47].
* [Fixed] Normalize line endings for release signing. See [#2364][48].
* [Added] Support more teams for Trello test cards. See [#2365][49].

## 0.10.0 / 2018-10-04

* [Added] Update base package paths. See [#2345][50].
* [Added] Add generic environment runner. See [#2342][51].
* [Added] Add WaitFor environment condition. See [#2343][52].
* [Added] Enable pytest plugin to control environments. See [#2336][53].

## 0.9.0 / 2018-09-30

* [Added] Allow testing of specific environments. See [#2312][54].
* [Added] Add run command. See [#2319][55].
* [Fixed] Fix namespace overwriting. See [#2311][56].
* [Fixed] Upgrade in-toto to gain full cross-platform release signing support. See [#2315][57].
* [Added] Command to validate metadata. See [#2269][58].

## 0.8.1 / 2018-09-25

* [Fixed] Fix Python 2 unicode handling for log pattern error message. See [#2303][59].

## 0.8.0 / 2018-09-25

* [Added] Add new templates for other integration types. See [#2285][60].
* [Added] Add release signing via in-toto. See [#2224][61].
* [Added] Add prometheus metadata.csv and metric map auto-generation. See [#2117][62].
* [Added] Keep track of the checks changed at every Datadog Agent release. See [#2277][63].

## 0.7.0 / 2018-09-18

* [Added] Fix manifest validation policy. See [#2258][64].
* [Added] Add config option to select the default repository. See [#2243][65].

## 0.6.2 / 2018-09-14

* [Fixed] Revert "Update base package paths (#2235)". See [#2240][66].

## 0.6.1 / 2018-09-14

* [Fixed] Move datadog_checks_base code into sub base package. See [#2167][67].

## 0.6.0 / 2018-09-14

* [Added] Update base package paths. See [#2235][68].
* [Added] Add ability to add wait time in docker_run. See [#2196][69].
* [Added] Add better debugging to test command. See [#2194][70].
* [Fixed] Gracefully handle tags that already exist. See [#2172][71].
* [Fixed] Fix release freeze command. See [#2188][72].
* [Added] Add ability to filter checks to test by changes. See [#2163][73].

## 0.5.0 / 2018-09-04

* [Added] Allow automated releasing by looking at github labels. See [#2169][74].
* [Fixed] Handle character limit for Trello card descriptions. See [#2162][75].

## 0.4.1 / 2018-08-31

* [Fixed] Fix trello command for other repos. See [#2155][76].

## 0.4.0 / 2018-08-28

* [Added] Add code coverage. See [#2105][77].
* [Added] Add command to create new integrations. See [#2037][78].

## 0.3.1 / 2018-08-03

* [Fixed] Fix clean command. See [#1992][79].

## 0.3.0 / 2018-07-30

* [Added] Allow passing --build to compose up. See [#1962][80].
* [Fixed] When setting repo paths do not resolve home. See [#1953][81].
* [Added] Add command to create Trello test cards from Agent release diffs. See [#1934][82].
* [Added] Add openldap to the list of agent integrations. See [#1923][83].
* [Added] Update dep tooling to support environment markers. See [#1921][84].

## 0.2.2 / 2018-07-19

* [Fixed] Relax condition error handling to allow more time. See [#1914][85].
* [Fixed] Do not skip release builds. See [#1913][86].
* [Fixed] Fix packaging of agent requirements. See [#1911][87].

## 0.2.1 / 2018-07-17

* [Fixed] make remove_path util more resilient to errors. See [#1900][88].

## 0.2.0 / 2018-07-17

* [Added] improve docker tooling. See [#1891][89].

## 0.1.1 / 2018-07-12

* [Fixed] fix changed-only test logic. See [#1878][90].

## 0.1.0 / 2018-07-12

* [Added] Add developer package. See [#1862][91].
[1]: https://github.com/DataDog/integrations-core/pull/2854
[2]: https://github.com/DataDog/integrations-core/pull/2879
[3]: https://github.com/DataDog/integrations-core/pull/2878
[4]: https://github.com/DataDog/integrations-core/pull/2816
[5]: https://github.com/DataDog/integrations-core/pull/2764
[6]: https://github.com/DataDog/integrations-core/pull/2808
[7]: https://github.com/DataDog/integrations-core/pull/2794
[8]: https://github.com/DataDog/integrations-core/pull/2736
[9]: https://github.com/DataDog/integrations-core/pull/2746
[10]: https://github.com/DataDog/integrations-core/pull/2782
[11]: https://github.com/DataDog/integrations-core/pull/2771
[12]: https://github.com/DataDog/integrations-core/pull/2765
[13]: https://github.com/DataDog/integrations-core/pull/2759
[14]: https://github.com/DataDog/integrations-core/pull/2724
[15]: https://github.com/DataDog/integrations-core/pull/2689
[16]: https://github.com/DataDog/integrations-core/pull/2664
[17]: https://github.com/DataDog/integrations-core/pull/2645
[18]: https://github.com/DataDog/integrations-core/pull/2647
[19]: https://github.com/DataDog/integrations-core/pull/2641
[20]: https://github.com/DataDog/integrations-core/pull/2642
[21]: https://github.com/DataDog/integrations-core/pull/2613
[22]: https://github.com/DataDog/integrations-core/pull/2617
[23]: https://github.com/DataDog/integrations-core/pull/2600
[24]: https://github.com/DataDog/integrations-core/pull/2599
[25]: https://github.com/DataDog/integrations-core/pull/2593
[26]: https://github.com/DataDog/integrations-core/pull/2503
[27]: https://github.com/DataDog/integrations-core/pull/2502
[28]: https://github.com/DataDog/integrations-core/pull/2491
[29]: https://github.com/DataDog/integrations-core/pull/2478
[30]: https://github.com/DataDog/integrations-core/pull/2474
[31]: https://github.com/DataDog/integrations-core/pull/2465
[32]: https://github.com/DataDog/integrations-core/pull/2444
[33]: https://github.com/DataDog/integrations-core/pull/2432
[34]: https://github.com/DataDog/integrations-core/pull/2457
[35]: https://github.com/DataDog/integrations-core/pull/2455
[36]: https://github.com/DataDog/integrations-core/pull/2454
[37]: https://github.com/DataDog/integrations-core/pull/2447
[38]: https://github.com/DataDog/integrations-core/pull/2430
[39]: https://github.com/DataDog/integrations-core/pull/2427
[40]: https://github.com/DataDog/integrations-core/pull/2416
[41]: https://github.com/DataDog/integrations-core/pull/2418
[42]: https://github.com/DataDog/integrations-core/pull/2411
[43]: https://github.com/DataDog/integrations-core/pull/2406
[44]: https://github.com/DataDog/integrations-core/pull/2408
[45]: https://github.com/DataDog/integrations-core/pull/2399
[46]: https://github.com/DataDog/integrations-core/pull/2375
[47]: https://github.com/DataDog/integrations-core/pull/2386
[48]: https://github.com/DataDog/integrations-core/pull/2364
[49]: https://github.com/DataDog/integrations-core/pull/2365
[50]: https://github.com/DataDog/integrations-core/pull/2345
[51]: https://github.com/DataDog/integrations-core/pull/2342
[52]: https://github.com/DataDog/integrations-core/pull/2343
[53]: https://github.com/DataDog/integrations-core/pull/2336
[54]: https://github.com/DataDog/integrations-core/pull/2312
[55]: https://github.com/DataDog/integrations-core/pull/2319
[56]: https://github.com/DataDog/integrations-core/pull/2311
[57]: https://github.com/DataDog/integrations-core/pull/2315
[58]: https://github.com/DataDog/integrations-core/pull/2269
[59]: https://github.com/DataDog/integrations-core/pull/2303
[60]: https://github.com/DataDog/integrations-core/pull/2285
[61]: https://github.com/DataDog/integrations-core/pull/2224
[62]: https://github.com/DataDog/integrations-core/pull/2117
[63]: https://github.com/DataDog/integrations-core/pull/2277
[64]: https://github.com/DataDog/integrations-core/pull/2258
[65]: https://github.com/DataDog/integrations-core/pull/2243
[66]: https://github.com/DataDog/integrations-core/pull/2240
[67]: https://github.com/DataDog/integrations-core/pull/2167
[68]: https://github.com/DataDog/integrations-core/pull/2235
[69]: https://github.com/DataDog/integrations-core/pull/2196
[70]: https://github.com/DataDog/integrations-core/pull/2194
[71]: https://github.com/DataDog/integrations-core/pull/2172
[72]: https://github.com/DataDog/integrations-core/pull/2188
[73]: https://github.com/DataDog/integrations-core/pull/2163
[74]: https://github.com/DataDog/integrations-core/pull/2169
[75]: https://github.com/DataDog/integrations-core/pull/2162
[76]: https://github.com/DataDog/integrations-core/pull/2155
[77]: https://github.com/DataDog/integrations-core/pull/2105
[78]: https://github.com/DataDog/integrations-core/pull/2037
[79]: https://github.com/DataDog/integrations-core/pull/1992
[80]: https://github.com/DataDog/integrations-core/pull/1962
[81]: https://github.com/DataDog/integrations-core/pull/1953
[82]: https://github.com/DataDog/integrations-core/pull/1934
[83]: https://github.com/DataDog/integrations-core/pull/1923
[84]: https://github.com/DataDog/integrations-core/pull/1921
[85]: https://github.com/DataDog/integrations-core/pull/1914
[86]: https://github.com/DataDog/integrations-core/pull/1913
[87]: https://github.com/DataDog/integrations-core/pull/1911
[88]: https://github.com/DataDog/integrations-core/pull/1900
[89]: https://github.com/DataDog/integrations-core/pull/1891
[90]: https://github.com/DataDog/integrations-core/pull/1878
[91]: https://github.com/DataDog/integrations-core/pull/1862
