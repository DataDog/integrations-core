# Style

-----

These are all the checkers used by our [style enforcement](../ddev/plugins.md#style).

## [black][black-github]

An opinionated formatter, like JavaScript's [prettier][prettier-github] and Golang's [gofmt][gofmt-docs].

## [isort][isort-github]

A tool to sort imports lexicographically, by section, and by type. We use the 5 standard sections: `__future__`, stdlib, third party, first party, and local.

`datadog_checks` is configured as a first party namespace.

## [flake8][flake8-github]

An easy-to-use wrapper around [pycodestyle][pycodestyle-github] and [pyflakes][pyflakes-github]. We select everything it provides and only ignore a few things to give precedence to other tools.

### [bugbear][flake8-bugbear-github]

A `flake8` plugin for finding likely bugs and design problems in programs. We enable:

- `B001`: Do not use bare `except:`, it also catches unexpected events like memory errors, interrupts, system exit, and so on. Prefer `except Exception:`.
- `B003`: Assigning to `os.environ` doesn't clear the environment. Subprocesses are going to see outdated variables, in disagreement with the current process. Use `os.environ.clear()` or the `env=` argument to Popen.
- `B006`: Do not use mutable data structures for argument defaults. All calls reuse one instance of that data structure, persisting changes between them.
- `B007`: Loop control variable not used within the loop body. If this is intended, start the name with an underscore.
- `B301`: Python 3 does not include `.iter*` methods on dictionaries. The default behavior is to return iterables. Simply remove the `iter` prefix from the method. For Python 2 compatibility, also prefer the Python 3 equivalent if you expect that the size of the dict to be small and bounded. The performance regression on Python 2 will be negligible and the code is going to be the clearest. Alternatively, use `six.iter*`.
- `B305`: `.next()` is not a thing on Python 3. Use the `next()` builtin. For Python 2 compatibility, use `six.next()`.
- `B306`: `BaseException.message` has been deprecated as of Python 2.6 and is removed in Python 3. Use `str(e)` to access the user-readable message. Use `e.args` to access arguments passed to the exception.
- `B902`: Invalid first argument used for method. Use `self` for instance methods, and `cls` for class methods.

### [logging-format][flake8-logging-format-github]

A `flake8` plugin for ensuring a consistent logging format. We enable:

-  `G001`: Logging statements should not use `string.format()` for their first argument
-  `G002`: Logging statements should not use `%` formatting for their first argument
-  `G003`: Logging statements should not use `+` concatenation for their first argument
-  `G004`: Logging statements should not use `f"..."` for their first argument (only in Python 3.6+)
-  `G010`: Logging statements should not use `warn` (use `warning` instead)
-  `G100`: Logging statements should not use `extra` arguments unless whitelisted
-  `G201`: Logging statements should not use `error(..., exc_info=True)` (use `exception(...)` instead)
-  `G202`: Logging statements should not use redundant `exc_info=True` in `exception`

## [Mypy][mypy-github]

A type checker allowing a mix of dynamic and static typing. This is optional for now.
