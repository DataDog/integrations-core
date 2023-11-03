# Config models

-----

All integrations use [pydantic](https://github.com/pydantic/pydantic) models as the primary way to validate and interface with configuration.

As [config spec](config-specs.md) data types are based on OpenAPI 3, we [automatically generate](https://github.com/koxudaxi/datamodel-code-generator) the necessary code.

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

- `InstanceConfig` (ID: `instance`) that corresponds to a check's entry in the `instances` section
- `SharedConfig` (ID: `shared`) that corresponds to the `init_config` section that is shared by all instances

All models are defined in `<ID>.py` and are available for import directly under `config_models`.

## Default values

The default values for optional settings are populated in `defaults.py` and are derived from the
[value](config-specs.md#values) property of config spec options. The precedence is the `default` key
followed by the `example` key (if it appears to represent a real value rather than an illustrative example
and the `type` is a primitive). In all other cases, the default is `None`, which means there is no default
getter function.

## Validation

The validation of fields for every model occurs in three high-level stages, as described in this section.

### Initial

```python
def initialize_<ID>(values: dict[str, Any], **kwargs) -> dict[str, Any]:
    ...
```

If such a validator exists in `validators.py`, then it is called once with the raw config that was supplied by the user.
The returned mapping is used as the input config for the subsequent stages.

### Field

The value of each field goes through the following steps.

#### Default value population

If a field was not supplied by the user nor during the [initialization stage](#initial), then its default value is
taken from `defaults.py`. This stage is skipped for required fields.

#### Custom field validators

The contents of `validators.py` are entirely custom and contain functions to perform extra validation if necessary.

```python
def <ID>_<OPTION_NAME>(value: Any, *, field: pydantic.fields.FieldInfo, **kwargs) -> Any:
    ...
```

Such validators are called for the appropriate field of the proper model. The returned value is used as the
new value of the option for the subsequent stages.

!!! note
    This only occurs if the option was supplied by the user.

#### Pre-defined field validators

A `validators` key under the [value](https://datadoghq.dev/integrations-core/meta/config-specs/#values) property of config
spec options is considered. Every entry refers to a relative import path to a [field validator](#custom-field-validators)
under `datadog_checks.base.utils.models.validation` and is executed in the defined order.

!!! note
    This only occurs if the option was supplied by the user.

#### Conversion to immutable types

Every `list` is converted to `tuple` and every `dict` is converted to [types.MappingProxyType](https://docs.python.org/3/library/types.html#types.MappingProxyType).

!!! note
    A field or nested field would only be a `dict` when it is defined as a mapping with arbitrary keys. Otherwise, it would be a model with its own properties as usual.

### Final

```python
def check_<ID>(model: pydantic.BaseModel) -> pydantic.BaseModel:
    ...
```

If such a validator exists in `validators.py`, then it is called with the final constructed model. At this point, it cannot
be mutated, so you can only raise errors.

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

It exposes the instantiated `InstanceConfig` model as `self.config` and `SharedConfig` model as `self.shared_config`.

## Immutability

In addition to each field being [converted to an immutable type](#conversion-to-immutable-types), all generated models are [configured as immutable](https://docs.pydantic.dev/2.0/usage/models/#faux-immutability).

## Deprecation

Every option marked as deprecated in the config spec will log a warning with information about when it will be removed and what to do.

## Enforcement

A validation command [`validate models`](../ddev/cli.md#ddev-validate-models) runs in our CI. To locally generate the proper files, run `ddev validate models [INTEGRATION] --sync`.
