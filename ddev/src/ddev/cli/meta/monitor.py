import click


@click.group
def monitor():
    """
    Work with monitors.
    """


@monitor.command
@click.argument("export_json", type=click.File())
def create(export_json):
    """
    Create monitor spec from the JSON export of the monitor in the UI.

    After you've copied the JSON in the UI you can either save it as a file or pipe it to STDIN:

    \b
    pbpaste | ddev meta monitor create -
    """
    import json
    from datetime import date

    exported = json.load(export_json)
    today = date.today().isoformat()
    wrangled = {
        "version": 2,
        "created_at": today,
        "last_updated_at": today,
        "title": click.edit(text=exported["name"], require_save=False),
        "description": click.edit(text="This monitor will alert you for XXX.", require_save=False),
        "tags": exported["tags"],
        "definition": exported,
    }
    click.echo(
        json.dumps(
            wrangled,
            indent=2,
        )
    )
