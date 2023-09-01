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
          - template: init_config
            options:
            - name: foo
              description: words
              value:
                type: string
          - template: instances
            options:
            - name: foo
              description: words
              value:
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
        from .shared import SharedConfig


        class ConfigMixin:
            _config_model_instance: InstanceConfig
            _config_model_shared: SharedConfig

            @property
            def config(self) -> InstanceConfig:
                return self._config_model_instance

            @property
            def shared_config(self) -> SharedConfig:
                return self._config_model_shared
        """
    )

    shared_model_contents, shared_model_errors = files['shared.py']
    assert not shared_model_errors
    assert shared_model_contents == normalize_yaml(
        """
        from __future__ import annotations

        from typing import Optional

        from pydantic import BaseModel, ConfigDict, field_validator, model_validator

        from datadog_checks.base.utils.functions import identity
        from datadog_checks.base.utils.models import validation

        from . import validators


        class SharedConfig(BaseModel):
            model_config = ConfigDict(
                validate_default=True,
                arbitrary_types_allowed=True,
                frozen=True,
            )
            foo: Optional[str] = None

            @model_validator(mode='before')
            def _initial_validation(cls, values):
                return validation.core.initialize_config(getattr(validators, 'initialize_shared', identity)(values))

            @field_validator('*', mode='before')
            def _validate(cls, value, info):
                field = cls.model_fields[info.field_name]
                field_name = field.alias or info.field_name
                if field_name in info.context['configured_fields']:
                    value = getattr(validators, f'shared_{info.field_name}', identity)(value, field=field)

                return validation.utils.make_immutable(value)

            @model_validator(mode='after')
            def _final_validation(cls, model):
                return validation.core.check_model(getattr(validators, 'check_shared', identity)(model))
        """
    )

    instance_model_contents, instance_model_errors = files['instance.py']
    assert not instance_model_errors
    assert instance_model_contents == normalize_yaml(
        """
        from __future__ import annotations

        from typing import Optional

        from pydantic import BaseModel, ConfigDict, field_validator, model_validator

        from datadog_checks.base.utils.functions import identity
        from datadog_checks.base.utils.models import validation

        from . import validators


        class InstanceConfig(BaseModel):
            model_config = ConfigDict(
                validate_default=True,
                arbitrary_types_allowed=True,
                frozen=True,
            )
            foo: Optional[str] = None

            @model_validator(mode='before')
            def _initial_validation(cls, values):
                return validation.core.initialize_config(getattr(validators, 'initialize_instance', identity)(values))

            @field_validator('*', mode='before')
            def _validate(cls, value, info):
                field = cls.model_fields[info.field_name]
                field_name = field.alias or info.field_name
                if field_name in info.context['configured_fields']:
                    value = getattr(validators, f'instance_{info.field_name}', identity)(value, field=field)

                return validation.utils.make_immutable(value)

            @model_validator(mode='after')
            def _final_validation(cls, model):
                return validation.core.check_model(getattr(validators, 'check_instance', identity)(model))
        """
    )
