---
title: Create a new Integration
kind: documentation
aliases:
    - /developers/integrations/integration_sdk/
    - /developers/integrations/testing/
---

To consider an Agent-based Integration complete, and thus ready to be included in the core repository and bundled with the Agent package, a number of prerequisites must be met:

* A `README.md` file with the right format
* A battery of tests verifying metrics collection
* A set of images to be used in the UI tile
* A `metadata.csv` file listing all of the collected metrics
* A complete `manifest.json` file
* If the Integration collects Service Checks, the `service_checks.json` must be complete as well

These requirements are used during the code review process as a checklist. This documentation covers the requirements and implementation details for a brand new Integration.

## Prerequisites

Python 2.7 needs to be available on your system. It is strongly recommended to create and activate a [Python virtual environment][5] in order to isolate the development environment. See the [Python Environment documentation][6] for more information.

You'll also need `docker-compose` in order to run the test harness.

## Setup

Clone the [integrations-extras repository][7]. By default, that tooling expects you to be working in the `$HOME/dd/` directory — this is optional and can be adjusted via configuration later.

```shell
mkdir $HOME/dd && cd $HOME/dd       # optional
git clone https://github.com/DataDog/integrations-extras.git
```

### Developer toolkit

The [developer toolkit][17] is comprehensive and includes a lot of functionality. Here's what you need to get started:

```
cd integrations-extras
pip install "datadog-checks-dev[cli]"
```

If you chose to clone this repository to somewhere other than `$HOME/dd/`, you'll need to adjust the configuration file:

```
ddev config set extras "/path/to/integrations-extras"
```

If you intend to work primarily on `integrations-extras`, set it as the default working repository:

```
ddev config set repo extras
```

## Scaffolding

One of the developer toolkit features is the `create` command, which creates the basic file and path structure (or "scaffolding") necessary for a new Integration.

### Dry-run

Let's try a dry-run, which won't write anything to disk. There are two important elements to note in the following command:
1. `-e`, which ensures that the scaffolding is created in the Extras repository.
2. `-n`, which is a dry-run (nothing gets written).

```
ddev -e create -n my_check
```

This will display the path where the files would have been written, as well as the structure itself. For now, just make sure that the path in the *first line* of output matches your Extras repository.

### Interactive mode

The interactive mode is a wizard for creating new Integrations. By answering a handful of questions, the scaffolding will be set up and lightly pre-configured for you.

```
ddev -e create my_check
```

After answering the questions, the output will match that of the dry-run above, except in this case the scaffolding for your new Integration will actually exist!

## Write the check

### Intro

A Check is a Python class with the following requirements:

* It must derive from `AgentCheck`
* It must provide a method with this signature: `check(self, instance)`

Checks are organized in regular Python packages under the `datadog_checks` namespace, so your code should live under `my_check/datadog_checks/my_check`. The only requirement is that the name of the package has to be the same as the check name. There are no particular restrictions on the name of the Python modules within that package, nor on the name of the class implementing the check.

### Implement check logic

Let's say we want to create a Service Check named `my_check` that checks for a string on a web page. It will result in `OK` if the string is present, `WARNING` if the page is accessible but the string was not found, and `CRITICAL` if the page is inaccessible.

The code would look something like this:

```python
import requests

from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException


# MyCheck derives from AgentCheck, and provides the required check method.
class MyCheck(AgentCheck):
    def check(self, instance):
        url = instance.get('url')
        search_string = instance.get('search_string')

        # It's a good idea to do some basic sanity checking. Try to be as
        # specific as possible, with the exceptions; you can fall back to
        # CheckException when in doubt though.
        if not url or not search_string:
            raise CheckException("Configuration error, please fix my_check.yaml")

        try:
            r = requests.get(url)
            r.raise_for_status()
            if search_string in r.text:
                # Page is accessible and the string is present.
                self.service_check('my_check.all_good', self.OK)
            else:
                # Page is accessible but the string was not found.
                self.service_check('my_check.all_good', self.WARNING)
        except Exception as e:
            # Something went horribly wrong. Ideally we'd be more specific…
            self.service_check('my_check.all_good', self.CRITICAL, e)
```

To learn more about the base Python class, see the [Python API documentation][2]. Moving along, let's dive into tests, which are an important part of any project (and *required* for inclusion in `integrations-extras`).

### Writing tests

There are two basic types of tests: unit tests for specific elements, and integration tests that execute the `check` method and verify proper metrics collection. Note that [pytest][3] and [tox][4] are used to run the tests.

For more information, see the [Datadog Checks Dev documentation][15].

The first part of the `check` method below retrieves two pieces of information we need from the configuration file. This is a good candidate for a unit test. Open the file at `my_check/tests/test_check.py` and replace the contents with something like this:

```python
import pytest

# Don't forget to import your Integration!
from datadog_checks.my_check import MyCheck
from datadog_checks.errors import CheckException


def test_config():
    c = MyCheck('my_check', {}, {}, None)

    # empty instance
    instance = {}
    with pytest.raises(CheckException):
        c.check(instance)

    # only url
    with pytest.raises(CheckException):
        c.check({'url': 'http://foobar'})

    # only string
    with pytest.raises(CheckException):
        c.check({'search_string': 'foo'})

    # this should be ok
    c.check({'url': 'http://foobar', 'search_string': 'foo'})
```

The scaffolding has already set up `tox` to run tests located at `my_check/tests`. Run the test:

```
ddev -e test my_check
```

The test we just wrote doesn't check our collection _logic_ though, so let's add an integration test. We will use `docker-compose` to spin up an Nginx container and let the check retrieve the welcome page. Create a compose file at `my_check/tests/docker-compose.yml` with the following contents:

```yaml
version: '3'
services:
  web:
    image: nginx:stable-alpine
    ports:
      - "8000:80"
```

Now add a dedicated `tox` environment to manage the tests, so that either the unit or integration tests can be run selectively during development. Note that the CI runs _all_ of the `tox` environments. Change your `tox.ini` file to this:

```ini
[tox]
minversion = 2.0
basepython = py27
envlist = unit, integration, flake8

[testenv]
platform = linux2|darwin
deps =
    datadog-checks-base
    -rrequirements-dev.txt

[testenv:unit]
commands =
    pip install --require-hashes -r requirements.txt
    pytest -v -m"not integration"

[testenv:integration]
commands =
    pip install --require-hashes -r requirements.txt
    pytest -v -m"integration"

[testenv:flake8]
skip_install = true
deps = flake8
commands = flake8 .

[flake8]
exclude = .eggs,.tox
max-line-length = 120
```

Note that when invoking `pytest` above, there is an extra argument: `-m"integration"` in one case, and `-m"not integration"` in another. These are called _attributes_ in pytest terms and `-m"integration"` tells pytest to only run tests that are marked with the `integration` attribute (or not, if `not integration` is specified).

Add the integration test to our `my_check/tests/test_check.py` module:

```python
import subprocess
import os
import time

from datadog_checks.utils.common import get_docker_hostname


@pytest.mark.integration
def test_service_check(aggregator):
    c = MyCheck('my_check', {}, {}, None)

    HERE = os.path.dirname(os.path.abspath(__file__))
    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'docker-compose.yml')
    ]

    # start the Nginx container
    subprocess.check_call(args + ["up", "-d"])
    time.sleep(5)  # we should implement a better wait strategy :)

    # the check should send OK
    instance = {
        'url': 'http://{}:8000'.format(get_docker_hostname()),
        'search_string': "Thank you for using nginx."
    }
    c.check(instance)
    aggregator.assert_service_check('my_check.all_good', MyCheck.OK)

    # the check should send WARNING
    instance['search_string'] = "Apache"
    c.check(instance)
    aggregator.assert_service_check('my_check.all_good', MyCheck.WARNING)

    # stop the container
    subprocess.check_call(args + ["down"])

    # the check should send CRITICAL
    c.check(instance)
    aggregator.assert_service_check('my_check.all_good', MyCheck.CRITICAL)
```

Run only the integration tests for faster iterations:

```
tox -e integration
```

The check is almost done. Let's add the final touches by adding the integration configurations.

## Configuration

### Configuration file

#### Parameters

Parameters in a configuration file follow these rules:

* Placeholders should always follow this format: `<THIS_IS_A_PLACEHOLDER>` according to the documentation [contributing guidelines][16]:
* All required parameters are **not** commented by default.
* All optional parameters are commented by default.
* If a placeholders has a default value for an integration (like the status endpoint of an integration), it can be used instead of a generic placeholder.

#### Parameters documentation

Each parameter in a configuration file must have a special comment block with the following format:

```yaml
## @<COMMAND_1> <ARG_COMMAND_1>
## @<COMMAND_2> <ARG_COMMAND_2>
## <DESCRIPTION>
#
<YAML_PARAM>: <PLACEHOLDER>
```

This paragraph contains **commands** which are a special string in the form `@command`. A command is valid only when the comment line containing it starts with a double `#` char:

```yaml
## @command this is valid

# @command this is not valid and will be ignored
```

`<DESCRIPTION>` is the description of the parameter. It can span across multiple lines in a special comment block.

##### Available commands

###### Param

The `@param` command aims to describe the parameter for documentation purposes.

```
@param <name> - <type> - <required> - default:<defval>
```

Arguments:

* `name`: the name of the parameter, e.g. `apache_status_url`
* `type`: the data type for the parameter value. Possible values:
  * *integer*
  * *double*
  * *string*
  * comma separated list of <*integer*|*double*|*string*>
* `required`: whether the parameter is required or not. Possible values:
    * *required*
    * *optional*
* `defval`: default value for the parameter, can be empty.

For instance, here is the `@param` *command* for the Apache integration check `apache_status_url` parameter:

```yaml
init_config:

instances:

  ## @param apache_status_url - string - required
  ## Status url of your Apache server.
  #
  - apache_status_url: http://localhost/server-status?auto
```

### Populate the README

The `README.md` file provided by our scaffolding already has the correct format. You must fill out the document with the relevant information.

### Add images and logos

The directory structure for images and logos:

```
    my_check/
    ├── images
    │   └── an_awesome_image.png
    └── logos
        ├── avatars-bot.png
        ├── saas_logos-bot.png
        └── saas_logos-small.png
```

The `images` folder contains all images that are used in the Integration tile. They must be referenced in the `## Overview` and/or `## Setup` sections in `README.md` as Markdown images using their public URLs. Because the `integrations-core` and `integrations-extras` repositories are public, a public URL can be obtained for any of these files via `https://raw.githubusercontent.com`:

```markdown
![snapshot](https://raw.githubusercontent.com/DataDog/integrations-extras/master/MyCheck/images/snapshot.png)
```

The `logos` folder must contain **three** images with filenames and sizes that match the following specifications _exactly_. Underneath each specification is a list of places where the images may appear in the web app.

#### saas_logos-bot.png (200 × 128)

* Integration tile images at `/account/settings`
* Description heading at `/account/settings#integrations/{integration_name}`
* Integration monitor tiles and search bar results images at `/monitors#create/integration`

#### saas_logos-small.png (120 × 60)

* Integration dashboards list images at `/dash/list`
* Some Integration dashboards/screenboards at `/dash/integration/{integration_dash_name}`

#### avatars-bot.png (128 × 128)

* Event stream at `/event/stream`
* Notification icons at `/report/monitor`

### Metadata

Review the contents of `manifest.json` and `metadata.csv`. The metadata catalog is not currently automatically generated, so filling it out manually is a crucial part of the release process.

#### manifest.json

Find below the complete list of mandatory and optional attributes for your `manifest.json` file:

| Attribute            | Type            | Mandatory/Optional | Description                                                                                                                                                                                                              |
| -------------------- | --------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `categories`         | Array of String | Mandatory          | Integration categories used on the [public documentation Integrations page][12].                                                                                                                                         |
| `creates_events`     | Boolean         | Mandatory          | If the integration should be able to create events. If this is set to `false`, attempting to create an event from the integration results in an error.                                                                   |
| `display_name`       | String          | Mandatory          | Title displayed on the corresponding integration tile in the Datadog application and on the [public documentation Integrations page][12]                                                                                 |
| `guid`               | String          | Mandatory          | Unique ID for the integration. [Generate a UUID][13]                                                                                                                                                                     |
| `is_public`          | Boolean         | Mandatory          | If set to `false` the integration `README.md` content is not indexed by bots in the Datadog public documentation.                                                                                                        |
| `maintainer`         | String          | Mandatory          | Email of the owner of the integration.                                                                                                                                                                                   |
| `manifest_version`   | String          | Mandatory          | Version of the current manifest.                                                                                                                                                                                         |
| `name`               | String          | Mandatory          | Unique name for the integration. Use the folder name for this parameter.                                                                                                                                                 |
| `public_title`       | String          | Mandatory          | Title of the integration displayed on the documentation. Should follow the following format: `Datadog-<INTEGRATION_NAME> Integration`.                                                                                   |
| `short_description`  | String          | Mandatory          | This text -Maximum 80 characters- appears at the top of the integration tile as well as the integration's rollover text on the integrations page.                                                                        |
| `support`            | String          | Mandatory          | Owner of the integration.                                                                                                                                                                                                |
| `supported_os`       | Array of String | Mandatory          | List of supported OSs. Choose among `linux`,`mac_os`, and `windows`.                                                                                                                                                     |
| `type`               | String          | Mandatory          | Type of the integration, should be set to `check`.                                                                                                                                                                       |
| `aliases`            | Array of String | Optional           | A list of URL aliases for the Datadog documentation.                                                                                                                                                                     |
| `description`        | String          | Optional           | This text appears when sharing an integration documentation link.                                                                                                                                                        |
| `is_beta`            | Boolean         | Optional           | Default `false`. If set to `true` the integration `README.md` content is not displayed in the Datadog public documentation.                                                                                              |
| `metric_to_check`    | String          | Optional           | The presence of this metric determines if this integration is working properly. If this metric is not being reported when this integration is installed, the integration is marked as broken in the Datadog application. |
| `metric_prefix`      | String          | Optional           | The namespace for this integration's metrics. Every metric reported by this integration will be prepended with this value.                                                                                               |
| `process_signatures` | Array of String | Optional           | A list of signatures that matches the command line of this integration.                                                                                                                                                  |

#### metadata.csv

Our example check doesn't send any metrics, so in this case we will leave it empty but find below the description for each column of your `metadata.csv` file:

| Column name     | Mandatory/Optional | Description                                                                                                                                                                     |
| ---             | ----               | ----                                                                                                                                                                            |
| `metric_name`   | Mandatory          | Name of the metric.                                                                                                                                                             |
| `metric_type`   | Mandatory          | [Type of the metric][10].                                                                                                                                                       |
| `interval`      | Optional           | Collection interval of the metric in second.                                                                                                                                    |
| `unit_name`     | Optional           | Unit of the metric. [Complete list of supported units][11].                                                                                                                     |
| `per_unit_name` | Optional           | If there is a unit sub-division, i.e `request per second`                                                                                                                       |
| `description`   | Optional           | Description of the metric.                                                                                                                                                      |
| `orientation`   | Mandatory          | Set to `1` if the metric should go up, i.e `myapp.turnover`. Set to `0` if the metric variations are irrelevant. Set to `-1` if the metric should go down, i.e `myapp.latency`. |
| `integration`   | Mandatory          | Name of the integration that emits the metric.                                                                                                                                  |
| `short_name`    | Mandatory          | Explicit Unique ID for the metric.                                                                                                                                              |

#### service_checks.json

Our check sends a Service Check, so we need to add it to the `service_checks.json` file:

```json
[
    {
        "agent_version": "6.0.0",
        "integration":"my_check",
        "check": "my_check.all_good",
        "statuses": ["ok", "warning", "critical"],
        "groups": ["host", "port"],
        "name": "All Good!",
        "description": "Returns `CRITICAL` if the check can't access the page."
    }
]
```

Find below the description for each attributes-each one of them is mandatory-of your `service_checks.json` file:

| Attribute       | Description                                                                                                              |
| ----            | ----                                                                                                                     |
| `agent_version` | Minimum Agent version supported.                                                                                         |
| `integration`   | Integration name.                                                                                                        |
| `check`         | Name of the Service Check                                                                                                |
| `statuses`      | List of different status of the check, to choose among `ok`, `warning`, and `critical`. `unknown` is also a possibility. |
| `groups`        | [Tags][14] sent with the Service Check.                                                                                  |
| `name`          | Displayed name of the Service Check.                                                                                     |
| `description`   | Description of the Service Check                                                                                         |

### Building

`setup.py` provides the setuptools setup script that helps us package and build the wheel. To learn more about Python packaging, take a look at [the official python documentation][9]

Once your `setup.py` is ready, create a wheel:

```
cd {integration}
python setup.py bdist_wheel
```

[1]: https://github.com/audreyr/cookiecutter
[2]: https://github.com/DataDog/datadog-agent/blob/6.2.x/docs/dev/checks/python/check_api.md
[3]: https://docs.pytest.org/en/latest/
[4]: https://tox.readthedocs.io/en/latest/
[5]: https://virtualenv.pypa.io/en/stable/
[6]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/python.md
[7]: https://github.com/DataDog/integrations-extras
[9]: https://packaging.python.org/tutorials/distributing-packages/
[10]: https://docs.datadoghq.com/developers/metrics/#metric-types
[11]: https://docs.datadoghq.com/developers/metrics/#units
[12]: https://docs.datadoghq.com/integrations/
[13]: https://www.uuidgenerator.net/
[14]: https://docs.datadoghq.com/getting_started/tagging/
[15]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev#development
[16]: https://github.com/DataDog/documentation/blob/master/CONTRIBUTING.md
[17]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev
