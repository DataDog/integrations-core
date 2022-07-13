import pluggy

spec = pluggy.HookspecMarker('ddev')


@spec
def register_commands():
    """Register new commands with the CLI."""
