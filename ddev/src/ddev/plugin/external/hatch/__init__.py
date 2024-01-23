from hatchling.plugin import hookimpl


@hookimpl
def hatch_register_environment_collector():
    from .environment_collector import DatadogChecksEnvironmentCollector

    return DatadogChecksEnvironmentCollector
