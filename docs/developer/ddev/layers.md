# What's in the box?

-----

<div align="center">
    <video preload="auto" autoplay loop muted>
        <source src="https://media.giphy.com/media/OuUZAQSyGSfHG/giphy.mp4" type="video/mp4"></source>
    </video>
</div>

The Dev package, often referred to as its [CLI](cli.md) entrypoint `ddev`, is fundamentally split into 2 parts.

## Test framework

The [test framework](test.md) provides everything necessary to test integrations, such as:

- Dependencies like [pytest](https://github.com/pytest-dev/pytest), [mock](https://github.com/testing-cabal/mock), [requests](https://github.com/psf/requests), etc.
- Utilities for consistently handling complex logic or common operations
- An [orchestrator](plugins.md#environment-manager) for arbitrary E2E environments

## CLI

The [CLI](cli.md) provides the interface through which tests are invoked, E2E environments are managed, and general repository maintenance (such as dependency management) occurs.

## Separation

As the dependencies of the test framework are a subset of what is required for the CLI, the
[CLI tooling](https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev/datadog_checks/dev/tooling) may import from the test framework located at
[the root](https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev/datadog_checks/dev), but not vice versa.
