# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.tooling.configuration.consumers.model.model_consumer import VALIDATORS_DOCUMENTATION

from ...utils import get_model_consumer, normalize_yaml


def test():
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          options:
          - template: instances
            options:
            - name: foo
              required: true
              description: words
              value:
                type: string
            - name: example
              description: words
              value:
                example: bar
                type: string
            - name: default_precedence
              description: words
              value:
                example: bar
                default: baz
                type: string
            - name: example_ignored_array
              description: words
              value:
                example:
                - test
                type: array
                items:
                  type: string
            - name: example_ignored_object
              description: words
              value:
                example:
                  key: value
                type: object
                additionalProperties: true
            - name: long_default_formatted
              description: words
              value:
                default:
                - ["01", "02", "03", "04", "05"]
                - ["06", "07", "08", "09", "10"]
                - ["11", "12", "13", "14", "15"]
                - ["16", "17", "18", "19", "20"]
                - ["21", "22", "23", "24", "25"]
                type: array
                items:
                  type: array
                  items:
                    type: string
        """
    )

    model_definitions = consumer.render()
    assert len(model_definitions) == 1

    files = model_definitions['test.yaml']
    assert len(files) == 4

    validators_contents, validators_errors = files['validators.py']
    assert not validators_errors
    assert validators_contents == VALIDATORS_DOCUMENTATION

    package_root_contents, package_root_errors = files['__init__.py']
    assert not package_root_errors
    assert package_root_contents == normalize_yaml(
        """
        from .instance import InstanceConfig


        class ConfigMixin:
            _config_model_instance: InstanceConfig

            @property
            def config(self) -> InstanceConfig:
                return self._config_model_instance
        """
    )

    defaults_contents, defaults_errors = files['defaults.py']
    assert not defaults_errors
    assert defaults_contents == '\n' + normalize_yaml(
        """
        def instance_default_precedence():
            return 'baz'


        def instance_example():
            return 'bar'


        def instance_long_default_formatted():
            return [
                ['01', '02', '03', '04', '05'],
                ['06', '07', '08', '09', '10'],
                ['11', '12', '13', '14', '15'],
                ['16', '17', '18', '19', '20'],
                ['21', '22', '23', '24', '25'],
            ]
        """
    )

    instance_model_contents, instance_model_errors = files['instance.py']
    assert not instance_model_errors
    assert instance_model_contents == normalize_yaml(
        """
        from __future__ import annotations

        from types import MappingProxyType
        from typing import Any, Optional

        from pydantic import BaseModel, ConfigDict, field_validator, model_validator

        from datadog_checks.base.utils.functions import identity
        from datadog_checks.base.utils.models import validation

        from . import defaults, validators


        class InstanceConfig(BaseModel):
            model_config = ConfigDict(
                validate_default=True,
                arbitrary_types_allowed=True,
                frozen=True,
            )
            default_precedence: Optional[str] = None
            example: Optional[str] = None
            example_ignored_array: Optional[tuple[str, ...]] = None
            example_ignored_object: Optional[MappingProxyType[str, Any]] = None
            foo: str
            long_default_formatted: Optional[tuple[tuple[str, ...], ...]] = None

            @model_validator(mode='before')
            def _initial_validation(cls, values):
                return validation.core.initialize_config(getattr(validators, 'initialize_instance', identity)(values))

            @field_validator('*', mode='before')
            def _validate(cls, value, info):
                field = cls.model_fields[info.field_name]
                field_name = field.alias or info.field_name
                if field_name in info.context['configured_fields']:
                    value = getattr(validators, f'instance_{info.field_name}', identity)(value, field=field)
                else:
                    value = getattr(defaults, f'instance_{info.field_name}', lambda: value)()

                return validation.utils.make_immutable(value)

            @model_validator(mode='after')
            def _final_validation(cls, model):
                return validation.core.check_model(getattr(validators, 'check_instance', identity)(model))
        """
    )
