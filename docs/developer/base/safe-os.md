# safe_os

-----

Whenever a check reads a file, lists a directory, or runs a subprocess, use the interface the base class
provides rather than calling `open`, `os`, `shutil`, `glob`, or `subprocess` directly:

```python
with self.safe_os.open(self.instance['log_path']) as f:
    contents = f.read()
```

Every method is a thin passthrough to the stdlib call it replaces, preceded by a validation hook. With
validation disabled, which is the default, behavior is identical to the call it replaces: the same exception
types and timing, the same permission bits on created files, the same encodings, and the same laziness.

The reason to route through it is that integrations accept paths from configuration. A file path, a
`bin_dir`, or a path to a binary the check executes can all come from a config provider that is not
trusted. The interface is the single place where those paths are checked before use, so the decision does
not have to be repeated correctly at every call site.

## Which binding to use

There are two ways to reach the interface, and choosing the wrong one silently disables validation.

Use `self.safe_os` for anything that touches a config-derived path. It is bound to a validator built
from the check's own security configuration, and it is the only binding that can enforce anything.

There is also a module-level `safe_os` singleton. It is permanently bound to the no-op validator and
has no injection point, so validation can never be attached to it. It exists only for code that has no
check instance and touches paths configuration cannot influence, such as loading a bundled asset shipped
inside the wheel.

A module-level helper that needs the interface should take it as a parameter rather than importing the
singleton:

```python
def get_version(osx, cmd):
    # `osx` is required rather than defaulted, so a caller cannot accidentally
    # get the unenforcing singleton.
    return osx.run(cmd.split(), capture_output=True, text=True)


class MyCheck(AgentCheck):
    def check(self, _):
        get_version(self.safe_os, self.instance['binary'])
```

`ddev validate safe-os` enforces both rules: it flags raw stdlib I/O in check code, and it flags use of
the singleton in a module that defines a check class. When a call genuinely cannot involve a config-derived
path, waive it with an inline `# SKIP_SAFE_OS_VALIDATION` comment explaining why. The comment can span
several lines and applies to the call directly below it.

## Available operations

| Category | Methods |
| --- | --- |
| Reading | `open`, `os_open` |
| Predicates | `exists`, `isfile`, `isdir`, `islink`, `getsize`, `access`, `stat` |
| Listing | `listdir`, `scandir`, `walk`, `glob` |
| Resolution | `realpath`, `resolve_path`, `validate_path`, `which` |
| Copying | `copy` |
| Subprocesses | `run`, `popen`, `get_subprocess_output` |

`get_subprocess_output` is kept as its own method rather than folded into `run`, because it delegates to the
base helper and so preserves that helper's output decoding, empty-output handling, and logging.

### Paths handed to third-party libraries

Some libraries open a path themselves, so the read cannot be intercepted: `ssl.SSLContext`, `psutil`,
`duckdb.connect`, and the FoundationDB client all do this. For those, validate the path at the handoff, which
is the last point the check controls:

```python
context.load_verify_locations(cafile=self.safe_os.validate_path(self.instance['ssl_cafile']))
```

Use `validate_path` rather than `resolve_path` here. Both validate, but `resolve_path` also normalizes, which
rewrites a relative path to an absolute one and therefore changes the value the library receives. That breaks
parity with passing the raw path through. Reach for `resolve_path` only when you actually want the resolved
form.

## Executables

`run`, `popen`, and `get_subprocess_output` validate every program the command will actually launch, not
just the first element of the argv. Two cases matter:

- A wrapper such as `sudo` puts the real program later in the argv. `sudo {ceph_cmd}` is validated on
  `ceph_cmd`, not only on `sudo`.
- With `shell=True`, the program the OS launches is the shell. That is what gets validated, since checking
  the first word of the command string would report on a program that never runs. Prefer passing an argv
  list instead of using `shell=True`.

A bare command name such as `gunicorn` is resolved through `PATH` before being checked, because that is how
the OS resolves it.

## When validation applies

Validation is governed by the existing `integration_ignore_untrusted_file_params` Agent setting, the same
switch that controls config-field validation at load time. There is no separate switch for point-of-use
validation: enabling that setting turns on both.

That has a consequence worth planning for. An operator who already relies on field validation will begin
enforcing at every migrated call site as soon as this ships, and a path that was previously only checked when
it arrived as a config field is now also checked when it is used. There is no dry-run mode, so the way to
assess impact is the excluded-checks setting and a staged rollout rather than an observation period.

Validation never applies to a trusted provider, or to a check listed in the excluded-checks setting, matching
load-time behavior exactly.

## Testing

The `mock_safe_os` fixture replaces the interface at both bindings at once, so a test does not need to
know which one the check uses:

```python
def test_version(aggregator, mock_safe_os):
    mock_safe_os.set_command_output(['mytool', '--version'], stdout='mytool 1.2.3')
    ...
```

It also provides an in-memory filesystem through `add_file`, `add_files`, `add_dir`, and `add_symlink`, and
every method is a `MagicMock`, so `return_value`, `side_effect`, and the `assert_*` helpers all work as
usual.

The fixture is all-or-nothing: it redirects every method to the fake. A test that needs to mock a single
operation and let other I/O reach the real filesystem should patch that one method instead:

```python
with mock.patch.object(check.safe_os, 'get_subprocess_output', return_value=(out, '', 0)):
    ...
```

## Limitations

This is a mediation layer for direct standard-library I/O. It is not a containment boundary, and the
following are explicitly out of scope:

- Paths opened inside a third-party library, beyond validating the path at the handoff as shown above.
- The shared TLS context builder, which resolves its own configuration and has no check reference, so the
  certificate paths it hands to `ssl` are not yet validated.
- Anything a subprocess does once it has been launched.
- What a shell string executes under `shell=True`, beyond validating the shell itself.
