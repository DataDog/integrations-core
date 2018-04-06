# How to create a new integration

To consider an Agent based integration complete thus ready to be included in the
core repository and bundled with the Agent package, a number of requisites have
to be met:

* readme
* test
* tile
* metadata.csv
* manifest
* service check metadata
* TODO

Those requirements will be used during the code review process as a checklist.
This howto will show you how to implement one by one all the requirements for a
brand new integrations.

## Prerequisites

Python 2.7 needs to be available on your system, see [this page](python.md) if
you need guidance for setting it up along with a virtual environment manager.

Before starting, we suggest to create and activate a Python virtual environment
so that all the packages we're going to install will be isolated from the system
wide installation.

## Setup

Clone the [integrations extras respository](https://github.com/DataDog/integrations-extras)
and point your shell at the root:

```
git clone https://github.com/DataDog/integrations-extras.git && cd integrations-extras
```

Install the Python packages needed to work on Agent integrations:

```
pip install -r requirements-dev.txt
```
