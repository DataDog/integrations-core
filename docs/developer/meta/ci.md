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
are executed in lexicographical order. Files in the scripts directory whose names begin with an underscore are not executed. 

## Validations

In addition to running tests on our CI, there are also some validations that are run to check for correctness of changes to various components of integrations. If any of these validations fail on your branch, then the CI will fail.


In short, each validation is a ``ddev`` command, which fails if the component it is validating is not correct.

See the [ddev documentation](../ddev/cli.md#ddev-validate) and [source code](https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev/datadog_checks/dev/tooling/commands/validate) for the full docs for each validation.

!!! tip
    A list of the current validations can be found [here](https://github.com/DataDog/integrations-core/blob/master/.azure-pipelines/templates/run-validations.yml).


### CI configuration

```
ddev validate ci
```

This validates that all CI entries for integrations are valid. This includes checking if the integration has the correct [codecov][codecov-home] config, and has a valid CI entry if it is testable.

!!! tip
    Run `ddev validate ci --fix` to resolve most errors.

### Agent requirements

```
ddev validate agent-reqs
```

This validates that each integration version is in sync with the [`requirements-agent-release.txt`](https://github.com/DataDog/integrations-core/blob/master/requirements-agent-release.txt) file. It is uncommon for this to fail because the release process is automated.

### Codeowners

```
ddev validate codeowners
```

This validates that every integration has a [codeowner entry](https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/about-code-owners). If you fail this validation, add an entry in the [codewners file](https://github.com/DataDog/integrations-extras/blob/master/.github/CODEOWNERS) corresponding to any newly added integration.

Note: This validation command is only run when contributing to [integrations-extras](https://github.com/DataDog/integrations-extras)

### Default configuration files

```
ddev validate config
```
This verifies that the config specs for all integrations are valid by enforcing our configuration spec [schema](config-specs.md#schema). The most common failure at this validation stage is some version of `File <INTEGRATION_SPEC> needs to be synced.` To resolve this issue, you can run `ddev validate config --sync`

If you see failures regarding formatting or missing parameters, see our [config spec](config-specs.md#schema) documentation for more details on how to construct configuration specs.

### Dashboard definition files

```
ddev validate dashboards
```

This validates that dashboards are formatted correctly. This means that they need to be proper JSON and generated from Datadog's `/dashboard` [API](https://docs.datadoghq.com/api/v1/dashboards/).

!!! tip
    If you see a failure regarding use of the screen endpoint, consider using our dashboard [utility command](../ddev/cli.md#ddev-meta-dash-export) to generate your dashboard payload.

### Dependencies

```
ddev validate dep
```

This command:

- Verifies the uniqueness of dependency versions across all checks.
- Verifies all the dependencies are pinned.
- Verifies the embedded Python environment defined in the base check and requirements listed in every integration are compatible.


This validation only applies if your work introduces new external dependencies.

### Manifest files

```
ddev validate manifest
```

This validates that the manifest files contain required fields, are formatted correctly, and don't contain common errors. See the [Datadog docs](https://docs.datadoghq.com/developers/integrations/check_references/#manifest-file) for more detailed constraints.

### Metadata

```
ddev validate metadata
```

This checks that every `metadata.csv` file is formatted correctly. See the [Datadog docs](https://docs.datadoghq.com/developers/integrations/check_references/#metrics-metadata-file) for more detailed constraints.

### README files

```
ddev validate readmes
```

This ensures that every integration's README.md file is formatted correctly. The main purpose of this validation is to ensure that any image linked in the readme exists and that all images are located in an integration's `/image` directory.

### Saved views data

```
ddev validate saved-views
```

This validates that saved views for an integration are formatted correctly and contain required fields, such as "type".

!!! tip
    View [example saved views](https://github.com/DataDog/integrations-core/tree/master/postgres/assets/saved_views) for inspiration and guidance.

### Service check data

```
ddev validate service-checks
```

This checks that every service check file is formatted correctly. See the [Datadog docs](https://docs.datadoghq.com/developers/integrations/check_references/#service-check-file) for more specific constraints.

### Imports

```
ddev validate imports
```
This verifies that all integrations import the base package in the correct way, such as:

```python
from datadog_checks.base.foo import bar
```

!!! tip
    See the [New Integration Instructions](https://docs.datadoghq.com/developers/integrations/new_check_howto/?tab=configurationtemplate#implement-check-logic) for more examples of how to use the base package.

## Labeler

We use a [GitHub Action][github-actions-labeler] to automatically add labels to pull requests.

!!! tip
    If the Labeler CI step fails on your PR, it's probably because your PR is from a fork. Don't worry if this happens- the team can manually add labels for you.

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
