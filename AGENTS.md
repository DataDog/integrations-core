# Development Guidelines

## General Development Guidelines

* Auto-format code with `ddev test -fs`.

## Python Type Hinting

### Generating new code

When generating python code, always add type hinting to the methods. Use modern syntaxis, for example, instead of using `Optional[str]` use `str | None` and instead of using `List[str]` use `list[str]`.

If a method yields a value but we are not returning anything or we do not accept anything sent to the generator, it is better to type the method as Iterator to explicitely expose the API of the method as simply something the caller can iterate over.

### Refactoring code

When refactoring existing code, never add type hints to method that are not type hinted unless asked explicitely.

### The case of AnyStr

AnyStr is normally used to define the type of a variable that can be either a string or bytes. This is soon to be deprecated and, instead, type parameter lits are a better solution. If AnyStr is used as type of several arguments in a given method signature, it is better to use type parameter lists and define the function as a generic function.

```python
# Soon to be deprecated
def func(a: AnySTr, b: AnyStr):
    pass

# Preferred
def func[T: (str, bytes)](a: T, b: T):
    pass
```

This way, whether a and b are either strings or bytes, they cannot be mixed.

If a single argument is present in the function, `str | bytes` is preferred.

## Configuration Models

**Applicable to:** `**/config_models/*.py`, `*/assets/configuration/spec.yaml`

Don't modify files in `**/config_models/*.py` directly. To change those files edit assets/configuration/spec.yaml and then run the following commands:

```shell
ddev -x validate config -s <INTEGRATION_NAME>
ddev -x validate models -s <INTEGRATION_NAME>
```

## Testing

Run unit and integration tests with `ddev --no-interactive test <INTEGRATION>`. For example, for the pgbouncer integration, run `ddev --no-interactive test pgbouncer`.

Run E2E tests with `ddev --no-interactive env test <INTEGRATION> --dev`. For example, for the pgbouncer integration, run `ddev --no-interactive env test pgbouncer --dev`.

Run specific tests with `ddev --no-interactive test <INTEGRATION> -- -k <PYTEST_FILTER_STRING>`, for example `ddev --no-interactive test kuma -- -k test_code_class_injection -s`.

## Code Formatting

Format code with `ddev test -fs <INTEGRATION>`. For example, for the pgbouncer integration, run `ddev test -fs pgbouncer`.

## Changelog Management

Changelog entries are typically generated using the `ddev` command and are required for all Python changes in `datadog_checks` subdirectories. Changelog entries are not required for changes in tests or assets.

Changelog files are named `<PR_NUMBER>.<TYPE>` and placed in the integration's `changelog.d/` directory.

### Version Bumping Behavior

* `fixed` - Bug fixes. Bumps the **patch** version (e.g., 1.0.0 → 1.0.1)
* `added` - New features. Bumps the **minor** version (e.g., 1.0.0 → 1.1.0)
* `changed` - Breaking changes or significant modifications. Bumps the **major** version (e.g., 1.0.0 → 2.0.0)

### Command Format

`ddev release changelog new <TYPE> <INTEGRATION> -m "<MESSAGE>"`

### Examples

```shell
# New feature
ddev release changelog new added kafka_consumer -m "Bump OpenSSL in confluent-kafka to 3.4.1 on Windows."

# Bug fix
ddev release changelog new fixed sqlserver -m "Fix a bug where ``tempdb`` is wrongly excluded from database files metrics due to all instances inherited from ``SqlserverDatabaseMetricsBase`` share the same reference of auto-discovered databases."

# Breaking change
ddev release changelog new changed postgres -m "Update configuration options for connection pooling."
```

## Documentation

### New files added

When a new file is added make sure to make it available through the navigation configuration in the mkdocs file. If it is not clear where it should go, ask.

### Style

Maintain style consistent. The style should be technical and professional.

Do not start lines/paragraphs with an inline code.
