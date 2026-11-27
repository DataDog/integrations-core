# ddev: output and display

ddev sends user-facing output through the display API on `Application` (inherited from `Terminal` in `ddev/src/ddev/cli/terminal.py`), not `print`. That keeps formatting consistent, respects `-q`/`-v` and color settings, and keeps output capturable in tests. Commands get it through `@click.pass_obj` as `app` (or `ctx.obj`). `terminal.py` is the source of truth for the methods and their semantics.

## The display API

- No `print`, `click.echo`, `app.console.print` or hand-rolled colors and status prefixes: use the display API. Exceptions: `print` for GitHub annotations in `application.py`, and Rich renderables printed with `markup=False`. `app.output` and `app.escaped_output` are the raw path.
- **Data goes to stdout, status to stderr.** `display_info`, `display_success` and the other `display_*` methods write to stderr, and `-q` hides them. Output a workflow or a user's pipe reads (JSON, values written to `$GITHUB_OUTPUT`) uses `app.output` or `app.display`, never a `display_*` method (**Request**).
- Use the most semantic method that fits: info, success, warning, error (through `app.abort` for failures), debug.
- Raw command output that may contain Rich markup is escaped (`escaped_output`).

## Diagnostics and logging

- Diagnostics shown with `-v` use `display_debug`. `app.logger` is fixed at WARNING, so its debug and info lines never show, whatever the verbosity. The Dispatcher uses structlog (`ddev.monitoring`) instead.
- A useful question for any new line: would a normal user need it to understand the command's result? If yes, it's display output. If it's only useful when debugging ddev, it's `display_debug`.

## Long-running work and CI

- Long-running work uses `app.status`, not manual spinners or progress output.
- Problems reported in CI use `app.annotate_error`, `app.annotate_warning` or `app.annotate_display_queue`, not hand-printed `::error::` lines (**Suggestion**).

## Common failure modes

- A `display_*` call used for output a workflow parses: it lands on stderr and disappears with `-q`.
- Diagnostic chatter shown as normal info output, or user-facing output hidden in `app.logger`.
- An error displayed while the command still exits 0.
- Raw output rendered without escaping when it may contain Rich markup.
