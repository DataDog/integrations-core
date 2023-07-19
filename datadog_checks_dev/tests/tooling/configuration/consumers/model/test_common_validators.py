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
                validators:
                - pkg.subpkg2.validate2
                - pkg.subpkg2.validate1
            - name: tags
              description: words
              value:
                type: array
                items:
                  type: string
                validators:
                - pkg.subpkg1.validate2
                - pkg.subpkg1.validate1
        """
    )

    model_definitions = consumer.render()
    assert len(model_definitions) == 1

    files = model_definitions['test.yaml']
    assert len(files) == 3

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

    instance_model_contents, instance_model_errors = files['instance.py']
    assert not instance_model_errors
    assert instance_model_contents == normalize_yaml(
        """
        from __future__ import annotations

        from typing import Optional, Sequence

        from pydantic import BaseModel, ConfigDict, field_validator, model_validator

        from datadog_checks.base.utils.functions import identity
        from datadog_checks.base.utils.models import validation

        from . import validators


        class InstanceConfig(BaseModel):
            model_config = ConfigDict(
                validate_default=True,
                frozen=True,
            )
            foo: str
            tags: Optional[Sequence[str]] = None

            @model_validator(mode='before')
            def _initial_validation(cls, values):
                return validation.core.initialize_config(getattr(validators, 'initialize_instance', identity)(values))

            @field_validator('*')
            def _run_validations(cls, value, info):
                field = cls.model_fields[info.field_name]
                field_name = field.alias or info.field_name
                if field_name not in info.context['configured_fields']:
                    return value

                return getattr(validators, f'instance_{info.field_name}', identity)(value, field=field)

            @field_validator('foo')
            def _run_foo_pkg_subpkg2_validate2(cls, value, info):
                field = cls.model_fields[info.field_name]
                field_name = field.alias or info.field_name
                if field_name not in info.context['configured_fields']:
                    return value

                return validation.pkg.subpkg2.validate2(value, field=field)

            @field_validator('foo')
            def _run_foo_pkg_subpkg2_validate1(cls, value, info):
                field = cls.model_fields[info.field_name]
                field_name = field.alias or info.field_name
                if field_name not in info.context['configured_fields']:
                    return value

                return validation.pkg.subpkg2.validate1(value, field=field)

            @field_validator('tags')
            def _run_tags_pkg_subpkg1_validate2(cls, value, info):
                field = cls.model_fields[info.field_name]
                field_name = field.alias or info.field_name
                if field_name not in info.context['configured_fields']:
                    return value

                return validation.pkg.subpkg1.validate2(value, field=field)

            @field_validator('tags')
            def _run_tags_pkg_subpkg1_validate1(cls, value, info):
                field = cls.model_fields[info.field_name]
                field_name = field.alias or info.field_name
                if field_name not in info.context['configured_fields']:
                    return value

                return validation.pkg.subpkg1.validate1(value, field=field)

            @field_validator('*', mode='after')
            def _make_immutable(cls, value):
                return validation.utils.make_immutable(value)

            @model_validator(mode='after')
            def _final_validation(cls, model):
                return validation.core.check_model(getattr(validators, 'check_instance', identity)(model))
        """
    )
