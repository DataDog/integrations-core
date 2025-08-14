import click

from ddev.cli.application import Application


@click.command(short_help="Run a bare OpenMetrics check on an OpenMetrics endpoint")
@click.option("-e", "--endpoint", help="The OpenMetrics endpoint to run the check on")
@click.option("-n", "--namespace", help="The namespace to use for the check", default="test", show_default=True)
@click.pass_obj
def dump(app: Application, endpoint: str, namespace: str):
    """
    Run a bare OpenMetrics check and dump all metrics as a check would see them.

    This command is useful if you want to see the full list of metrics exposed by an OpenMetrics endpoint
    as they will be emitted by a check. It does not include any custom metrics/tags renaming.

    !!! warning "Base extra"
        This command is only available if ddev is installed with the `base` extra.

        ```
        pipx install ddev[base]
        ```
    """
    import os

    from datadog_checks.base.checks.openmetrics.v2.base import OpenMetricsBaseCheckV2
    from datadog_checks.base.stubs import aggregator

    os.environ["DDEV_SKIP_GENERIC_TAGS_CHECK"] = "true"

    class BareCheck(OpenMetricsBaseCheckV2):
        __NAMESPACE__ = namespace

    check = BareCheck(namespace, {}, [{"metrics": [".*"], "openmetrics_endpoint": endpoint}])
    errors = check.run()

    if errors:
        import json

        body = json.loads(errors)[0]
        app.display_error(f"\nError Message: {body['message']}")
        app.display_error(body["traceback"])
        return

    for metric_name in aggregator._metrics:
        app.display(metric_name)
