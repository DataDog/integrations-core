# Continuous integration

-----

## Tests

All Agent Integrations use [Azure Pipelines][azp-home] to execute tests.

### Execution

Every runner will execute test stages in the following order:

1. Unit & integration
1. [E2E](../e2e.md#testing)
1. [Benchmarks](../ddev/test.md#benchmarks)

### Platforms

We make extensive use of [Microsoft-hosted agents][azp-agents].

- [Windows-only][azp-templates-windows] integrations run on [Windows Server 2019 with Visual Studio 2019][azp-agents-latest-windows]
- [All other][azp-templates-linux] integrations run on [Ubuntu 18.04 LTS][azp-agents-latest-linux]

Some things are tested on multiple platforms, like the [base package](../base/about.md) and the Disk check.

### Pipelines

#### Pull requests

Every commit to a branch tied to an open pull request triggers a [Linux and Windows job][azp-pipeline-changes]. Each
runner will test any integration that was [changed](../testing.md#detection), with the Windows runner being further
restricted to Windows-only integrations.

If the [base package](../base/about.md) is modified, jobs will be [triggered][azp-pipeline-changes-all] for every
integration, similar to the [pipeline for master](#master).

#### Master

Every commit to the `master` branch triggers one or more jobs for [every integration][azp-templates-all-core].

### Scripts

Some integrations require additional set up such as the installation of system dependencies. As we only want these
extra steps to occur when necessary, there is a [stage][azp-templates-setup] ran for every job that will detect what
needs to be done and execute the appropriate [scripts][azp-scripts]. As integrations may need different set up on
different platforms, all scripts live under a directory named after the platform. All scripts in the directory
will be executed in lexicographical order.

## Validations

In addition to running tests on our CI, there are also some validation stages that check for correctness of changes to various components of integrations. If any of these validations fail on your branch, then CI will fail.


In short, each validation is a ``ddev`` command, which fails if the component it is validating is not correct.


!!! tip A list of the current validations can be found here:
https://github.com/DataDog/integrations-core/blob/master/.azure-pipelines/templates/run-validations.yml


### Validate CI configuration
```python
ddev validate ci
```

### Validate Agent requirements
```python
ddev validate agent-reqs
```

### Validate default configuration files
```python
ddev validate config
```
This verifies that the config specs for all integrations are valid by enforcing our configuration spec (schema)[config-specs.md#schema] . The most common failure at this validation stage is some version of `File <INTEGRATION_SPEC> needs to be synced.` To resolve this issue, you can run `ddev validate config --sync`

If you see failures regarding formatting or missing parameters, see our (config spec)[config-specs.md#schema] documentation.

### Validate dashboard definition files
```python
ddev validate dashboards
```

This validates that dashboards are formatted correctly. This means that they need to be proper JSON and generated from Datadog's `/screen` (API)[https://docs.datadoghq.com/dashboards/guide/screenboard-api-doc/?tab=python]

If you see a failure regarding use of the screen endpoint, consider using our dashboard [utility command](../ddev/cli.md#export) to generate your dashboard payload.

### Validate dependencies
ddev validate dep

### Validate manifest files
ddev validate manifest -i
https://docs.datadoghq.com/developers/integrations/check_references/#manifest-file

### ddev validate metadata
```python
ddev validate metadata
```
https://docs.datadoghq.com/developers/integrations/check_references/#metrics-metadata-file
This checks that every `metadata.csv` file is formatted correctly

### Validate saved views data
```python
ddev validate saved-views
```

This validates that saved views for an integration are formatted correctly and contain required fields, such as "type".


### Validate service check data
ddev validate service-checks

https://docs.datadoghq.com/developers/integrations/check_references/#service-check-file

### Validate imports
ddev validate imports

## Labeler

We use a [GitHub Action][github-actions-labeler] to automatically add labels to pull requests.

The labeler is [configured][github-actions-labeler-config] to add the following:

| Label | Condition |
| --- | --- |
| <mark style="background-color: #bfdadc; color: #000000">integration/&lt;NAME&gt;</mark> | any directory at the root that actually contains an integration |
| <mark style="background-color: #7e1df4; color: #ffffff">documentation</mark> | any Markdown, [config specs](config-specs.md), `manifest.json`, or anything in `/docs/` |
| <mark style="background-color: #6ad86c; color: #000000">dev/testing</mark> | [Codecov][codecov-home] or [Azure Pipelines][azp-home] config |
| <mark style="background-color: #6ad86c; color: #000000">dev/tooling</mark> | [GitLab][gitlab-home] (see [CD](cd.md)), [GitHub Actions][github-actions-home], or [Stale bot](#stale-bot) config, or the `ddev` [CLI](../ddev/about.md#cli) |
| <mark style="background-color: #83fcf8; color: #000000">dependencies</mark> | any change in shipped dependencies |
| <mark style="background-color: #FFDF00; color: #000000">release</mark> | any [base package](../base/about.md), [dev package](../ddev/about.md), or integration release |
| <mark style="background-color: #eeeeee; color: #000000">changelog/no-changelog</mark> | any release, or if all files don't modify code that is shipped |

The <mark style="background-color: #d613a8; color: #ffffff">changelog/&lt;TYPE&gt;</mark> label must be [applied manually](../guidelines/pr.md#changelog-label).

### Fork

We forked the official action to support the following:

- actions/labeler!43
- actions/labeler!44
- a special `all:` prefix modifier indicating the pattern must match every file

## Docs

## Stale bot

We use a [GitHub App][github-apps-probot] that is [configured][github-apps-probot-config] to address abandoned issues and pull requests.
