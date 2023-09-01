# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.tooling.configuration.consumers.model.model_consumer import VALIDATORS_DOCUMENTATION

from ...utils import get_model_consumer, normalize_yaml


def test_enum_of_strings():
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          options:
          - template: instances
            options:
            - name: my_str
              description: words
              value:
                type: string
                example: 'a'
                enum:
                  - 'a'
                  - 'b'
                  - 'c'
        """
    )

    generated_model_definitions = consumer.render()
    assert len(generated_model_definitions) == 1

    generated_files = generated_model_definitions['test.yaml']
    assert len(generated_files) == 4

    validators_contents, validators_errors = generated_files['validators.py']
    assert not validators_errors
    assert validators_contents == VALIDATORS_DOCUMENTATION

    package_root_contents, package_root_errors = generated_files['__init__.py']
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

    defaults_contents, defaults_errors = generated_files['defaults.py']
    assert not defaults_errors
    assert defaults_contents == '\n' + normalize_yaml(
        """
        def instance_my_str():
            return 'a'
        """
    )

    instance_model_contents, instance_model_errors = generated_files['instance.py']
    assert not instance_model_errors
    instace_model_expected_contents = normalize_yaml(
        """
        from __future__ import annotations

        from typing import Optional

        from pydantic import BaseModel, ConfigDict, field_validator, model_validator
        from typing_extensions import Literal

        from datadog_checks.base.utils.functions import identity
        from datadog_checks.base.utils.models import validation

        from . import defaults, validators


        class InstanceConfig(BaseModel):
            model_config = ConfigDict(
                validate_default=True,
                arbitrary_types_allowed=True,
                frozen=True,
            )
            my_str: Optional[Literal['a', 'b', 'c']] = None

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
    assert instance_model_contents == instace_model_expected_contents


def test_enum_of_ints():
    consumer = get_model_consumer(
        """
        name: test
        version: 0.0.0
        files:
        - name: test.yaml
          options:
          - template: instances
            options:
            - name: my_int
              description: numbers
              value:
                type: integer
                example: 1
                enum:
                  - 1
                  - 2
                  - 3
        """
    )

    generated_model_definitions = consumer.render()
    assert len(generated_model_definitions) == 1

    generated_files = generated_model_definitions['test.yaml']
    assert len(generated_files) == 4

    validators_contents, validators_errors = generated_files['validators.py']
    assert not validators_errors
    assert validators_contents == VALIDATORS_DOCUMENTATION

    package_root_contents, package_root_errors = generated_files['__init__.py']
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

    defaults_contents, defaults_errors = generated_files['defaults.py']
    assert not defaults_errors
    assert defaults_contents == '\n' + normalize_yaml(
        """
        def instance_my_int():
            return 1
        """
    )

    instance_model_contents, instance_model_errors = generated_files['instance.py']
    assert not instance_model_errors
    instace_model_expected_contents = normalize_yaml(
        """
        from __future__ import annotations

        from typing import Optional

        from pydantic import BaseModel, ConfigDict, field_validator, model_validator
        from typing_extensions import Literal

        from datadog_checks.base.utils.functions import identity
        from datadog_checks.base.utils.models import validation

        from . import defaults, validators


        class InstanceConfig(BaseModel):
            model_config = ConfigDict(
                validate_default=True,
                arbitrary_types_allowed=True,
                frozen=True,
            )
            my_int: Optional[Literal[1, 2, 3]] = None

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
    assert instance_model_contents == instace_model_expected_contents
