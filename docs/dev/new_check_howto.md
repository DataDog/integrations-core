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

These requirements are used during the code review process as a checklist. This *howto* shows you how to implement all of the requirements for a brand new Integration.

## Prerequisites

Python 2.7 needs to be available on your system. It is strongly recommended to create and activate a [Python virtual environment][5] in order to isolate the development environment. See the [Python Environment documentation][6] for more information.

## Setup

Clone the [integrations extras repository][IntegrationsExtrasRepository] and point your shell at the root:

```
git clone https://github.com/DataDog/integrations-extras.git && cd integrations-extras
```

Install the Python packages needed to work on Agent integrations:

```
pip install -r requirements-dev.txt
```

[cookiecutter][1] is used to create the skeleton for a new integration:

```
cookiecutter https://github.com/DataDog/cookiecutter-datadog-check.git
```

Answer the questions when prompted. Once done, you should end up with something like this:

```
    my_check
    ├── CHANGELOG.md
    ├── MANIFEST.in
    ├── README.md
    ├── conf.yaml.example
    ├── datadog_checks
    │   ├── __init__.py
    │   └── foo_check
    │       ├── __about__.py
    │       ├── __init__.py
    │       └── foo_check.py
    ├── images
    │   └── snapshot.png
    ├── logos
    │   ├── avatars-bot.png
    │   ├── saas_logos-bot.png
    │   └── saas_logos-small.png
    ├── manifest.json
    ├── metadata.csv
    ├── requirements-dev.txt
    ├── requirements.in
    ├── requirements.txt
    ├── service_checks.json
    ├── setup.py
    ├── tests
    │   ├── __init__.py
    │   ├── conftest.py
    │   └── test_check.py
    └── tox.ini
```

## Write the check

### Intro

A Check is a Python class with the following requirements:

* It must derive from `AgentCheck`
* It must provide a method with this signature: `check(self, instance)`

Checks are organized in regular Python packages under the `datadog_checks` namespace, so your code should live under `my_check/datadog_checks/my_check`. The only requirement is that the name of the package has to be the same as the check name. There are no particular restrictions on the name of the Python modules within that package, nor the the name of the class implementing the check.

### Implement check logic

Let's say we want to collect a service check named `my_check` that sends `OK` when we are able to find a certain string in the body of a web page, `WARNING` if we can access the page but can't find the string, and `CRITICAL` if we can't reach the page at all.

The code would look like this:

```python
import requests

from datadog_checks.checks import AgentCheck
from datadog_checks.errors import CheckException


class MyCheck(AgentCheck):
    def check(self, instance):
        url = instance.get('url')
        search_string = instance.get('search_string')

        if not url or not search_string:
            raise CheckException("Configuration error, please fix my_check.yaml")

        try:
            r = requests.get(url)
            r.raise_for_status()
            if search_string in r.text:
                self.service_check(self.OK)
            else:
                self.service_check(self.WARNING)
        except Exception as e:
            self.service_check(self.CRITICAL, e)
```

To learn more about the base Python class, see the [Python API documentation][2]. Now let's write some tests and see if that works.

### Writing tests

There are two basic types of tests: unit tests for specific elements, and integration tests that execute the `check` method and verify proper metrics collection. Note that [pytest][3] and [tox][4] are used to run the tests. 

The first part of the `check` method below retrieves two pieces of information we need from the configuration file. This is a good candidate for a unit test. Open the file at `my_check/tests/test_check.py` and replace the contents with something like this:

```python
import pytest
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

The cookiecutter template has already setup `tox` to run tests located at `my_check/tests`. Run the test:

```
cd my_check && tox
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
tox -e integrations
```

The check is almost done. Let's add the final touches.

## Final touches

### Populate the README

The `README.md` file provided by our cookiecutter template already has the correct format. You must fill out the relevant sections - look for the ellipses `[...]`.

### Add images and logos

The directory structure for images and logos:

    my_check/
    ├── images
    │   └── an_awesome_image.png
    └── logos
        ├── avatars-bot.png
        ├── saas_logos-bot.png
        └── saas_logos-small.png

The `images` folder contains all images that are used in the Integration tile. They must be referenced in the `## Overview` and/or `## Setup` sections in `README.md` as Markdown images using their public URLs. Because the `integrations-core` and `integrations-extras` repositories are public, a public URL can be obtained for any of these files via `https://raw.githubusercontent.com`.

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

Review the contents of `manifest.json` and `metadata.csv`. The metadata catalog is not currently automatically generated, so filling it out manually is a crucial part of the release process. Our example check doesn't send any metrics however, so in this case we will leave it empty.

Our check sends a Service Check though, so we need to add it to the `service_checks.json` file:

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


[1]: https://github.com/audreyr/cookiecutter
[2]: https://github.com/DataDog/datadog-agent/blob/6.2.x/docs/dev/checks/python/check_api.md
[3]: https://docs.pytest.org/en/latest/
[4]: http://tox.readthedocs.io/en/latest/
[5]: https://virtualenv.pypa.io/en/stable/
[6]: https://github.com/DataDog/integrations-core/blob/master/docs/dev/python.md
[IntegrationsExtrasRepository]: https://github.com/DataDog/integrations-extras