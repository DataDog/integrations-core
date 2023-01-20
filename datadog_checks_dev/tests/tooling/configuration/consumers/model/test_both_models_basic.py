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
    assert len(files) == 5

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

    defaults_contents, defaults_errors = files['defaults.py']
    assert not defaults_errors
    assert defaults_contents == normalize_yaml(
        """
        from datadog_checks.base.utils.models.fields import get_default_field_value


        def shared_foo(field, value):
            return get_default_field_value(field, value)


        def instance_foo(field, value):
            return get_default_field_value(field, value)
        """
    )

    shared_model_contents, shared_model_errors = files['shared.py']
    assert not shared_model_errors
    assert shared_model_contents == normalize_yaml(
        """
        from __future__ import annotations

        from typing import Optional

        from pydantic import BaseModel, root_validator, validator

        from datadog_checks.base.utils.functions import identity
        from datadog_checks.base.utils.models import validation

        from . import defaults, validators


        class SharedConfig(BaseModel):
            class Config:
                allow_mutation = False

            foo: Optional[str]

            @root_validator(pre=True)
            def _initial_validation(cls, values):
                return validation.core.initialize_config(getattr(validators, 'initialize_shared', identity)(values))

            @validator('*', pre=True, always=True)
            def _ensure_defaults(cls, v, field):
                if v is not None or field.required:
                    return v

                return getattr(defaults, f'shared_{field.name}')(field, v)

            @validator('*')
            def _run_validations(cls, v, field):
                if not v:
                    return v

                return getattr(validators, f'shared_{field.name}', identity)(v, field=field)

            @root_validator(pre=False)
            def _final_validation(cls, values):
                return validation.core.finalize_config(getattr(validators, 'finalize_shared', identity)(values))
        """
    )

    instance_model_contents, instance_model_errors = files['instance.py']
    assert not instance_model_errors
    assert instance_model_contents == normalize_yaml(
        """
        from __future__ import annotations

        from typing import Optional

        from pydantic import BaseModel, root_validator, validator

        from datadog_checks.base.utils.functions import identity
        from datadog_checks.base.utils.models import validation

        from . import defaults, validators


        class InstanceConfig(BaseModel):
            class Config:
                allow_mutation = False

            foo: Optional[str]

            @root_validator(pre=True)
            def _initial_validation(cls, values):
                return validation.core.initialize_config(getattr(validators, 'initialize_instance', identity)(values))

            @validator('*', pre=True, always=True)
            def _ensure_defaults(cls, v, field):
                if v is not None or field.required:
                    return v

                return getattr(defaults, f'instance_{field.name}')(field, v)

            @validator('*')
            def _run_validations(cls, v, field):
                if not v:
                    return v

                return getattr(validators, f'instance_{field.name}', identity)(v, field=field)

            @root_validator(pre=False)
            def _final_validation(cls, values):
                return validation.core.finalize_config(getattr(validators, 'finalize_instance', identity)(values))
        """
    )
