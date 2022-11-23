---
title: Create an Agent Integration
kind: documentation
aliases:
  - /developers/integrations/integration_sdk/
  - /developers/integrations/testing/
  - /integrations/datadog_checks_dev/
  - /guides/new_integration/
---

## Overview

This guide provides instructions for creating a Datadog Agent integration in the `integrations-extras` repository. For more information about why you would want to create an Agent-based integration, see [Creating your own solution][1].

## Setup
### Prerequisites

The required Datadog Agent integration development tools include:

- Python v3.8 or later
- [Docker][2] to run the full test suite

Many operating systems come with a pre-installed version of Python. However, the version of Python installed by default may be older than the version used in the Agent, and may lack some required tools and dependencies. To ensure that you've everything you need to get an integration running, install a dedicated Python interpreter.

There are several options for installing Python, including:

- Following the [official Python documentation][3] to download and install the Python interpreter.
- Using a Python version manager like [pyenv][4].

Python v3.3 or later comes with a pre-installed version manager called `venv`, which is used on this page. Debian or Ubuntu installations do not come packaged with `venv`. You can install the `venv` package by running `sudo apt-get install python3-venv`.

## Prepare your development environment

Follow these instructions to set up your development environment:

1. Create the `dd` directory and clone the [`integrations-extras` repo][5].

   The Datadog Development Toolkit expects you to work in the `$HOME/dd/` directory. This is not mandatory, but working in a different directory requires additional configuration steps.

   To create the `dd` directory and clone the `integrations-extras` repo:
   ```shell
   mkdir $HOME/dd && cd $HOME/dd
   git clone https://github.com/DataDog/integrations-extras.git
   ```

1. Optionally, set up a [Python virtual environment][6] to isolate your development environment:

   ```shell
   cd $HOME/dd/integrations-extras
   python3 -m venv venv
   . venv/bin/activate
   ```

   **Tip**: If you ever need to exit the virtual environment, run `deactivate`.

1. Ensure the Python `wheel` package is installed and up-to-date:

   ```shell
   pip3 install wheel
   ```

1. Install the [Developer Toolkit][7]:

   ```bash
   pip3 install "datadog-checks-dev[cli]"
   ```

1. Optionally, if you cloned the `integrations-extras` to somewhere other than `$HOME/dd/`, adjust the configuration file:

   ```shell
   ddev config set extras "/path/to/integrations-extras"
   ```

1. Set `integrations-extras` as the default working repository:

   ```shell
   ddev config set repo extras
   ```

## Create your integration

Once you've downloaded Docker, installed an appropriate version of Python, and prepared your development environment, you can get started with creating an Agent-based integration. The instructions below use an example integration called `Awesome`. Follow along using the code from Awesome, or replace Awesome with your own code.

### Create scaffolding for your integration

The `ddev create` command runs an interactive tool that creates the basic file and path structure (or "scaffolding") necessary for a new Agent-based integration.

1. Before you create your first integration directory, try a dry-run using the `-n/--dry-run` flag, which doesn't write anything to the disk:

   ```bash
   ddev create -n Awesome
   ```

   This command displays the path where the files would have been written, as well as the structure itself. Make sure the path in the first line of output matches your `integrations-extras` repository location.

1. Run the command without the `-n` flag. The tool asks you for an email and name and then creates the files you need to get started with an integration.

   ```shell
   ddev create Awesome
   ```

## Write an Agent Check

At the core of each Agent-based integration is an *Agent Check* that periodically collects information and sends it to Datadog. Checks inherit their logic from the `AgentCheck` base class and have the the following requirements:

- Integrations running on the Datadog Agent v7 and later must be compatible with Python 3; however, Agents v5 and v6 still use Python 2.7.
- Checks must derive from `AgentCheck`.
- Checks must provide a method with this signature: `check(self, instance)`.
- Checks are organized in regular Python packages under the `datadog_checks` namespace. For example, the code for Awesome lives in the `awesome/datadog_checks/awesome/` directory.
- The name of the package must be the same as the check name.
- There are no restrictions on the name of the Python modules within that package, nor on the name of the class implementing the check.

### Implement check logic

For Awesome, the Agent Check is composed of a Service Check named `awesome.search` that searches for a string on a web page. It results in `OK` if the string is present, `WARNING` if the page is accessible but the string was not found, and `CRITICAL` if the page is inaccessible. To learn how to submit metrics with your Agent Check, see [Custom Agent Check][8].

The code contained within `awesome/datadog_checks/awesome/check.py` looks something like this:

{{< code-block lang="python" filename="check.py" collapsible="true" >}}
import requests

from datadog_checks.base import AgentCheck, ConfigurationError


class AwesomeCheck(AgentCheck):
    """AwesomeCheck derives from AgentCheck, and provides the required check method."""

    def check(self, instance):
        url = instance.get('url')
        search_string = instance.get('search_string')

        # It's a very good idea to do some basic sanity checking.
        # Try to be as specific as possible with the exceptions.
        if not url or not search_string:
            raise ConfigurationError('Configuration error, please fix awesome.yaml')

        try:
            response = requests.get(url)
            response.raise_for_status()
        # Something went horribly wrong
        except Exception as e:
            # Ideally we'd use a more specific message...
            self.service_check('awesome.search', self.CRITICAL, message=str(e))
        # Page is accessible
        else:
            # search_string is present
            if search_string in response.text:
                self.service_check('awesome.search', self.OK)
            # search_string was not found
            else:
                self.service_check('awesome.search', self.WARNING)
{{< /code-block >}}

To learn more about the base Python class, see [Anatomy of a Python Check][9].

## Write validation tests

There are two basic types of tests:

- [Unit tests for specific functionality.](#write-a-unit-test)
- [Integration tests that execute the `check` method and verify proper metrics collection.](#write-an-integration-test)

[pytest][10] and [hatch][11] are used to run the tests. Tests are required if you want your integration to be included in the `integrations-extras` repository.

### Write a unit test

The first part of the `check` method for Awesome retrieves and verifies two elements from the configuration file. This is a good candidate for a unit test. Open the file at `awesome/tests/test_awesome.py` and replace the contents with the following:

{{< code-block lang="python" filename="test_awesome.py" collapsible="true" >}}
import pytest

    # Don't forget to import your integration

from datadog_checks.awesome import AwesomeCheck
from datadog_checks.base import ConfigurationError


@pytest.mark.unit
def test_config():
    instance = {}
    c = AwesomeCheck('awesome', {}, [instance])

    # empty instance
    with pytest.raises(ConfigurationError):
        c.check(instance)

    # only the url
    with pytest.raises(ConfigurationError):
        c.check({'url': 'http://foobar'})

    # only the search string
    with pytest.raises(ConfigurationError):
        c.check({'search_string': 'foo'})

    # this should not fail
    c.check({'url': 'http://foobar', 'search_string': 'foo'})
{{< /code-block >}}

`pytest` has the concept of markers that can be used to group tests into categories. Notice that `test_config` is marked as a `unit` test.

The scaffolding is set up to run all the tests located in `awesome/tests`.

To run the tests, run:

```bash
ddev test awesome
```

### Write an integration test

The [unit test above](#write-a-unit-test) doesn't check the collection logic. To test the logic, you need to create an environment for an integration test and write an integration test.

#### Create an environment for the integration test

The toolkit uses `docker` to spin up an Nginx container and lets the check retrieve the welcome page.

To create an environment for the integration test, create a docker-compose file at `awesome/tests/docker-compose.yml` with the following contents:

{{< code-block lang="yaml" filename="docker-compose.yml" collapsible="true" >}}
version: "3"

services:
  nginx:
    image: nginx:stable-alpine
    ports:
      - "8000:80"
{{< /code-block >}}

Next, open the file at `awesome/tests/conftest.py` and replace the contents with the following:

{{< code-block lang="python" filename="conftest.py" collapsible="true" >}}
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here

URL = 'http://{}:8000'.format(get_docker_hostname())
SEARCH_STRING = 'Thank you for using nginx.'
INSTANCE = {'url': URL, 'search_string': SEARCH_STRING}


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(get_here(), 'docker-compose.yml')

    # This does 3 things:
    #
    # 1. Spins up the services defined in the compose file
    # 2. Waits for the url to be available before running the tests
    # 3. Tears down the services when the tests are finished
    with docker_run(compose_file, endpoints=[URL]):
        yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE.copy()
{{< /code-block >}}

#### Add an integration test

After you've setup an environment for the integration test, add an integration test to the `awesome/tests/test_awesome.py` file:

{{< code-block lang="python" filename="test_awesome.py" collapsible="true" >}}
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_service_check(aggregator, instance):
    c = AwesomeCheck('awesome', {}, [instance])

    # the check should send OK
    c.check(instance)
    aggregator.assert_service_check('awesome.search', AwesomeCheck.OK)

    # the check should send WARNING
    instance['search_string'] = 'Apache'
    c.check(instance)
    aggregator.assert_service_check('awesome.search', AwesomeCheck.WARNING)
{{< /code-block >}}

To speed up development, use the `-m/--marker` option to run integration tests only:

```bash
ddev test -m integration awesome
```

Your integration is almost complete. Next, add the necessary check assets.

## Create the check assets

The set of assets created by the `ddev` scaffolding must be populated in order for a check to be considered in `integrations-extras`:

`README.md`
: This contains the documentation for your Agent Check, how to set it up, which data it collects, and support information.

`spec.yaml`
: This is used to generate the `conf.yaml.example` using the `ddev` tooling (see the **Configuration template** tab below). For more information, see [Configuration specification][12].

`conf.yaml.example`
: This contains default (or example) configuration options for your Agent Check. **Do not edit this file by hand!** It is generated from the contents of `spec.yaml`. For more information, see the [Configuration file reference][13].

`manifest.json`
: This contains the metadata for your Agent Check such as the title and categories. For more information, see the [Manifest file reference][14].

`metadata.csv`
: This contains the list of all metrics collected by your Agent Check. For more information, see the [Metrics metadata file reference][15].

`service_check.json`
: This contains the list of all Service Checks collected by your Agent Check. For more information, see the [Service check file reference][16].

{{< tabs >}}
{{% tab "Configuration template" %}}

For this example, the `awesome/assets/configuration/spec.yaml` used to generate `awesome/datadog_checks/awesome/data/conf.yaml.example` appears in the following format:

```yaml
name: Awesome
files:
- name: awesome.yaml
  options:
  - template: init_config
    options:
    - template: init_config/default
  - template: instances
    options:
    - name: url
      required: true
      description: The URL to check.
      value:
        type: string
        example: http://example.org
    - name: search_string
      required: true
      description: The string to search for.
      value:
        type: string
        example: Example Domain
    - name: flag_follow_redirects
      # required: false is implicit; comment it to see what happens!
      required: false
      description: Follow 301 redirects.
      value:
        type: boolean
        example: false
    # Try transposing these templates to see what happens!
    #- template: instances/http
    - template: instances/default
```

To generate `conf.yaml.example` using `ddev`, run:

```bash
ddev validate config --sync awesome
```

{{% /tab %}}
{{% tab "Manifest" %}}

For this example, the `awesome/manifest.json` for the Awesome Service Check appears in the following format:

```json
{
  "manifest_version": "2.0.0",
  "app_uuid": "79eb6e54-2110-4d50-86c3-f7037d1a9daa", // Do not use this example UUID. UUIDs must be unique and valid.
  "app_id": "awesome",
  "classifier_tags": [
    "Supported OS::Linux",
    "Supported OS::Mac OS",
    "Supported OS::Windows"
  ],
  "display_on_public_website": false,
  "tile": {
    "overview": "README.md#Overview",
    "configuration": "README.md#Setup",
    "support": "README.md#Support",
    "changelog": "CHANGELOG.md",
    "description": "",
    "title": "Awesome",
    "media": []
  },
  "author": {
    "support_email": "email@example.org"
  },
  "oauth": {},
  "assets": {
    "integration": {
      "source_type_name": "Awesome",
      "configuration": {
        "spec": "assets/configuration/spec.yaml"
      },
      "events": {
        "creates_events": false
      },
      "metrics": {
        "prefix": "awesome.",
        "check": "",
        "metadata_path": "metadata.csv"
      },
      "service_checks": {
        "metadata_path": "assets/service_checks.json"
      }
    }
  }
}
```

{{% /tab %}}
{{% tab "Metadata" %}}

For this example, the Awesome integration doesn't provide any metrics, so in this case, the generated `awesome/metadata.csv` only contains only a row with the column names.

{{% /tab %}}
{{% tab "Service Check" %}}

For this example, the Awesome integration contains a Service Check, so you need to add it to the `awesome/assets/service_checks.json` file:

```json
[
  {
    "agent_version": "6.0.0",
    "integration": "awesome",
    "check": "awesome.search",
    "statuses": ["ok", "warning", "critical"],
    "groups": [],
    "name": "Awesome search!",
    "description": "Returns `CRITICAL` if the check can't access the page, `WARNING` if the search string was not found, or `OK` otherwise."
  }
]
```

{{% /tab %}}
{{< /tabs >}}

## Build the wheel

The `pyproject.toml` file provides the metadata that is used to package and build the wheel. The wheel contains the files necessary for the functioning of the integration itself, which includes the Check, configuration example file, and artifacts generated during the build of the wheel.

All additional elements, including the metadata files, are not meant to be contained within the wheel, and are used elsewhere by the Datadog platform and ecosystem. To learn more about Python packaging, see [Packaging Python Projects][17].

Once your `pyproject.toml` is ready, create a wheel:

- (Recommended) With the `ddev` tooling: `ddev release build <INTEGRATION_NAME>`.
- Without the `ddev` tooling: `cd <INTEGRATION_DIR> && pip wheel . --no-deps --wheel-dir dist`.

## Install the wheel

The wheel is installed using the Agent `integration` command, available in [Agent v6.10.0 and up][18]. Depending on your environment, you may need to execute this command as a specific user or with specific privileges:

**Linux** (as `dd-agent`):

```bash
sudo -u dd-agent datadog-agent integration install -w /path/to/wheel.whl
```

**OSX** (as admin):

```bash
sudo datadog-agent integration install -w /path/to/wheel.whl
```

**Windows PowerShell** (Ensure that your shell session has _administrator_ privileges):

<details>
  <summary>Agent <code>v6.11</code> or earlier</summary>
  
  ```ps
  & "C:\Program Files\Datadog\Datadog Agent\embedded\agent.exe" integration install -w /path/to/wheel.whl
  ```

</details>

<details open>
  <summary>Agent<code>v6.12</code> or later</summary>

  ```ps
  & "C:\Program Files\Datadog\Datadog Agent\bin\agent.exe" integration install -w /path/to/wheel.whl
  ```
</details>

## Review the checklist to publishing your integration

After you've created your Agent-based integration, refer to this list to make sure your integration contains all the required files and validations:

- A `README.md` file with the correct format and contents.
- A battery of tests verifying metrics collection.
- A `metadata.csv` file listing all of the collected metrics.
- A complete `manifest.json` file.
- If the integration collects Service Checks, the `service_checks.json` must be complete as well.

After you open a pull request in the `integrations-extras` repository, CI validation tests will run. These tests must be green before your pull request is merged and your integration tile is published.

## Further Reading

Additional helpful documentation, links, and articles:

- [Manage integrations via API calls][19]

[1]: https://docs.datadoghq.com/developers/#creating-your-own-solution
[2]: https://docs.docker.com/get-docker/
[3]: https://wiki.python.org/moin/BeginnersGuide/Download
[4]: https://github.com/pyenv/pyenv
[5]: https://github.com/DataDog/integrations-extras
[6]: https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/
[7]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev
[8]: https://docs.datadoghq.com/developers/metrics/agent_metrics_submission/
[9]: https://github.com/DataDog/datadog-agent/blob/6.2.x/docs/dev/checks/python/check_api.md
[10]: https://docs.pytest.org/en/latest
[11]: https://github.com/pypa/hatch
[12]: https://datadoghq.dev/integrations-core/meta/config-specs/
[13]: https://docs.datadoghq.com/developers/integrations/check_references/#configuration-file
[14]: https://docs.datadoghq.com/developers/integrations/check_references/#manifest-file
[15]: https://docs.datadoghq.com/developers/integrations/check_references/#metrics-metadata-file
[16]: https://docs.datadoghq.com/developers/integrations/check_references/#service-check-file
[17]: https://packaging.python.org/en/latest/tutorials/packaging-projects/
[18]: https://docs.datadoghq.com/agent/
[19]: https://www.datadoghq.com/blog/programmatically-manage-your-datadog-integrations/
