# Agent Integrations

[![Coverage status](https://codecov.io/github/DataDog/integrations-core/coverage.svg?branch=master)](https://codecov.io/github/DataDog/integrations-core?branch=master)
[![GitHub contributors](https://img.shields.io/github/contributors/DataDog/integrations-core)](https://github.com/DataDog/integrations-core)
[![Downloads](https://pepy.tech/badge/datadog-checks-dev)](https://pepy.tech/project/datadog-checks-dev)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/datadog-checks-dev)](https://pypi.org/project/datadog-checks-dev)
[![Code style - black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License - BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-9400d3.svg)](https://choosealicense.com/licenses/bsd-3-clause)

-----

Welcome to the wonderful world of developing Agent Integrations for Datadog. Here we document how we do things,
the processes for various tasks, coding conventions & best practices, the internals of our testing infrastructure,
and so much more.

If you are intrigued, continue reading. If not, continue all the same :point_down_tone2:

## Getting started

To work on any integration (a.k.a. [Check](faq/faq.md#integration-vs-check)), you must [setup](setup.md) your development environment.

After that you may immediately begin [testing](testing.md) or read through the [best practices](guidelines/style.md) we strive to follow.

Also, feel free to check out how [ddev](ddev/layers.md) works and browse the [API](base/api.md) reference of the base package.

## Navigation

Desktop readers can use keyboard shortcuts to navigate.

| Keys | Action |
| --- | --- |
| <ul><li><code>,</code> (comma)</li><li><code>p</code></li></ul> | Navigate to the "previous" page |
| <ul><li><code>.</code> (period)</li><li><code>n</code></li></ul> | Navigate to the "next" page |
| <ul><li><code>/</code></li><li><code>s</code></li></ul> | Display the search modal |
