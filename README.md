# Datadog Agent Integrations - Core

[![Build status][1]][2]
[![Build status][3]][4]
[![Coverage status][17]][18]
[![Documentation Status][19]][20]

This repository contains the Agent Integrations (also known as checks) that Datadog
officially develops and supports. To add a new integration, please see the [Integrations Extras][5]
repository and the [accompanying documentation][6].

The [Datadog Agent][7] packages are equipped with all the Integrations from this
repository, so to get started using them, you can simply [install the Agent][8]
for your operating system. The [AGENT_CHANGELOG](AGENT_CHANGELOG.md) file shows
which Integrations have been updated in each Agent version.

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

Now that integrations are cleanly defined as python packages, we will soon be able
to ship them as Python wheels that will be pip-installable in the Python environment
embedded into the Datadog Agent. This presents a paradigm change in the way we will
be delivering standalone integration upgrades, moving away from OS-specific packages
to idiomatic Python package delivery.

## Contributing

Working with integrations is easy, the main page of the [development docs][6]
contains all the info you need to get your dev enviroment up and running in minutes
to run, test and build a Check. More advanced API documentation can be found [here][20]

## Reporting Issues

For more information on integrations, please reference our [documentation][11]
and [knowledge base][12]. You can also visit our
[help page][13] to connect with us.

[1]: https://travis-ci.org/DataDog/integrations-core.svg?branch=master
[2]: https://travis-ci.org/DataDog/integrations-core
[3]: https://ci.appveyor.com/api/projects/status/8w4s2bilp48n43gw?svg=true
[4]: https://ci.appveyor.com/project/Datadog/integrations-core
[5]: https://github.com/DataDog/integrations-extras
[6]: https://docs.datadoghq.com/developers/integrations
[7]: https://github.com/DataDog/datadog-agent
[8]: https://docs.datadoghq.com/agent/
[9]: https://docs.pytest.org/en/latest/
[10]: https://packaging.python.org/tutorials/distributing-packages/
[11]: https://docs.datadoghq.com
[12]: https://help.datadoghq.com/hc/en-us
[13]: https://docs.datadoghq.com/help/
[15]: https://github.com/DataDog/integrations-core/blob/6.2.1/requirements-integration-core.txt
[16]: https://github.com/DataDog/integrations-core/blob/ea2dfbf1e8859333af4c8db50553eb72a3b466f9/requirements-agent-release.txt
[17]: https://codecov.io/github/DataDog/integrations-core/coverage.svg?branch=master
[18]: https://codecov.io/github/DataDog/integrations-core?branch=master
[19]: https://readthedocs.org/projects/datadog-checks-base/badge/?version=latest
[20]: https://datadog-checks-base.readthedocs.io/en/latest/?badge=latest
