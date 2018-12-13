# Datadog Agent Integrations - Core

[![Build status][1]][2]
[![Build status][2]][4]
[![Coverage status][3]][18]

This repository contains the Agent Integrations (also known as checks) that Datadog
officially develops and supports. To add a new integration, please see the [Integrations Extras][4]
repository and the [accompanying documentation][5].

The [Datadog Agent][6] packages are equipped
with all the checks from this repository, so to get started using them, you can
simply [install the Agent][7] for your operating
system.

General documentation about the project can be [found here][8]

## Integrations as Python wheels

When working with an integration, you will now be dealing with a more structured
python project. The new structure should help keep a more sane and modular codebase.
To help with the transition, please take a look at the following map to understand
where everything falls into place in the new approach.

| FORMER LOCATION               | NEW LOCATION                                      |
| ---------------               | ------------                                      |
| `{integration}/check.py`      | `{integration}/datadog_checks/{integration}/*.py` |
| `{integration}/test_check.py` | `{integration}/tests/*.py`                        |
| n/a                           | `{integration}/setup.py`                          |

## A note about installing

Now that integrations are cleanly defined as python packages, we will soon be able
to ship them as Python wheels that will be pip-installable in the Python environment
embedded into the Datadog Agent. This presents a paradigm change in the way we will
be delivering standalone integration upgrades, moving away from OS-specific packages
to idiomatic Python package delivery.

Agent releases starting from version 5.21 bundle the latest wheels for any
integration, but at the moment you can't upgrade or downgrade between releases.

Each Datadog Agent release will continue to ship a set of the most up to date stable integrations available. The `requirements-agent-release.txt` file at the root of this repo is the best place to check what Integration version is shipped with each Agent.

**Note** The release process is currently in flux as we move toward the ability to ship wheels independently of Agent releases. Due to this, the Changelog may show a version and release that isn't yet available to download. Please check the below table to see which Integration versions are shipped with your Agent install.

| Agent Version   | List of Shipped Integration Versions   |
| --------------- | -------------------------------------- |
| 6.2.1           | [Link][9]                             |
| 6.3.0           | [Link][10]                             |

## Quick Start

Working with integrations is easy, the main page of the [development docs][11]
contains all the info you need to get your dev enviroment up and running in minutes
to run, test and build a Check.

**Important:** the instructions are only valid for a subset of the Checks in this
repository. Making all the checks work with the new build and test strategy is
a work in progress. You can find the list of the checks already updated [here][12]

## Reporting Issues

For more information on integrations, please reference our [documentation][13]
and [knowledge base][14]. You can also visit our
[help page][15] to connect with us.

[1]: https://travis-ci.org/DataDog/integrations-core.svg?branch=master
[2]: https://ci.appveyor.com/api/projects/status/8w4s2bilp48n43gw?svg=true
[3]: https://codecov.io/github/DataDog/integrations-core/coverage.svg?branch=master
[4]: https://github.com/DataDog/integrations-extras
[5]: https://docs.datadoghq.com/developers/integrations/integration_sdk
[6]: https://github.com/DataDog/datadog-agent
[7]: https://docs.datadoghq.com/agent
[8]: docs/README.md
[9]: https://github.com/DataDog/integrations-core/blob/6.2.1/requirements-integration-core.txt
[10]: https://github.com/DataDog/integrations-core/blob/ea2dfbf1e8859333af4c8db50553eb72a3b466f9/requirements-agent-release.txt
[11]: docs/dev/README.md
[12]: https://github.com/DataDog/integrations-core/blob/master/tasks/constants.py#L15
[13]: https://docs.datadoghq.com
[14]: https://help.datadoghq.com/hc/en-us
[15]: https://docs.datadoghq.com/help
