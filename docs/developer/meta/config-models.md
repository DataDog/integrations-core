# Config models

-----

All integrations use [pydantic](https://github.com/samuelcolvin/pydantic) models as the primary way to validate and interface with configuration.

As config spec data types are based on OpenAPI 3, we [automatically generate](https://github.com/koxudaxi/datamodel-code-generator) the necessary code.

The models reside in a package named `config_models` located at the root of a check's namespaced package. For example, a new integration named `foo`:

```
foo
│   ...
├── datadog_checks
│   └── foo
│       └── config_models
│           ├── __init__.py
│           ├── defaults.py
│           ├── instance.py
│           ├── shared.py
│           └── validators.py
│       └── __init__.py
│       ...
...
```

There are 2 possible models:

- `SharedConfig` (ID: `shared`) that corresponds to the `init_config` section
- `InstanceConfig` (ID: `instance`) that corresponds to a check's entry in the `instances` section

All models are defined in `<ID>.py` and are available for import directly under `config_models`.

## Default values

The default values for optional settings are populated in `defaults.py` and are derived from the
[value](../meta/config-specs.md#values) property of config spec options.

The precedence is:

1. the `default` key
2. the `example` key, if it appears to represent a real value rather than an illustrative example and the `type` is a primitive
3. the default value of the `type` e.g. `string` -> `str()`, `object` -> `dict()`, etc.

## Validation

The validation of fields for every model occurs in 6 stages.

### Initial

```python
def initialize_<ID>(values: dict[str, Any], **kwargs) -> dict[str, Any]:
    ...
```

If such a validator exists in `validators.py`, then it is called once with the raw config that was supplied by the user.
The returned mapping is used as the input config for the subsequent stages.

### Default value population

If a field was not supplied by the user nor during the initialization stage, then its default value is
taken from `defaults.py`. This stage is skipped for required fields.

### Default field validators

At this point `pydantic` will parse the values and perform validation of types, etc.

### Custom field validators

The contents of `validators.py` are entirely custom and contain functions to perform extra validation if necessary.

```python
def <ID>_<OPTION_NAME>(value: Any, *, field: pydantic.fields.ModelField, **kwargs) -> Any:
    ...
```

Such validators are called for the appropriate field of the proper model if the option was supplied by the user.

The returned value is used as the new value of the option for the subsequent stages.

### Pre-defined field validators

A new `validators` key under the [value](https://datadoghq.dev/integrations-core/meta/config-specs/#values) property of config
spec options is considered. Every entry will refer to a relative import path to a [field validator](#custom-field-validators)
under `datadog_checks.base.utils.models.validation` and is executed in the defined order.

The last returned value is used as the new value of the option for the [final](#final) stage.

### Final

```python
def finalize_<ID>(values: dict[str, Any], **kwargs) -> dict[str, Any]:
    ...
```

If such a validator exists in `validators.py`, then it is called with the cumulative result of all fields.

The returned mapping is used to instantiate the model.

## Loading

A [check initialization](https://datadoghq.dev/integrations-core/base/basics/#check-initializations) occurs before a check's first
run that loads the config models. Validation errors will thus prevent check execution.

## Interface

The config models package contains a class `ConfigMixin` from which checks inherit:

```python
from datadog_checks.base import AgentCheck

from .config_models import ConfigMixin


class Check(AgentCheck, ConfigMixin):
    ...
```

It exposes the instantiated `InstanceConfig` model at `self.config` and `SharedConfig` model at `self.shared_config`.

## Immutability

All generated models are [configured as immutable](https://pydantic-docs.helpmanual.io/usage/models/#faux-immutability).
Additionally, every `list` is converted to `tuple` and every `dict` is converted to [immutables.Map](https://github.com/MagicStack/immutables).

## Deprecation

Every option marked as deprecated in the config spec will log a warning with information about when it will be removed and what to do.

## Enforcement

A validation command `ddev validate models` runs in our CI. To locally generate the proper files, run `ddev validate models [CHECK] --sync`.
