# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import inspect
from enum import Enum, unique
from functools import wraps

from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck


def argument_value(arg_name, func, *args, **kwargs):
    # Get the position of target_arg in function's signature
    params = list(inspect.signature(func).parameters)
    try:
        position = params.index(arg_name) - (1 if 'self' in params else 0)
    except ValueError:
        position = None
    # If argument passed positionally
    if position is not None and position < len(args):
        return args[position]
    # If argument passed by name
    elif arg_name in kwargs:
        return kwargs[arg_name]
    return None


def generate_hash(func, *args, **kwargs):
    name = func.__name__
    args_str = ','.join(map(str, args))
    kwargs_str = ','.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    combined = f"{name}({args_str},{kwargs_str})"
    return hash(combined)


class Component:
    registered_global_metric_methods = {}
    registered_project_metric_methods = {}

    @unique
    class Id(str, Enum):
        IDENTITY = 'identity'
        COMPUTE = 'compute'
        NETWORK = 'network'
        BLOCK_STORAGE = 'block-storage'
        BAREMETAL = 'baremetal'
        LOAD_BALANCER = 'load-balancer'
        IMAGE = 'image'

    @unique
    class Types(list, Enum):
        IDENTITY = ['identity']
        COMPUTE = ['compute']
        NETWORK = ['network']
        BLOCK_STORAGE = ['block-storage', 'volumev3']
        BAREMETAL = ['baremetal']
        LOAD_BALANCER = ['load-balancer']
        IMAGE = ['image']

    def http_error(report_service_check=False):
        def decorator_http_error(func):
            @wraps(func)  # Preserve function metadata
            def wrapper(self, *args, **kwargs):
                if report_service_check:
                    tags = argument_value('tags', func, *args, **kwargs)
                try:
                    result = func(self, *args, **kwargs)
                    if report_service_check:
                        tags = argument_value('tags', func, *args, **kwargs)
                        self.check.service_check(self.SERVICE_CHECK, AgentCheck.OK, tags=tags)
                    return result if result is not None else True
                except HTTPError as e:
                    self.check.log.error("HTTPError: %s", e.response)
                    if report_service_check:
                        self.check.service_check(self.SERVICE_CHECK, AgentCheck.CRITICAL, tags=tags)
                except Exception as e:
                    self.check.log.error("Exception: %s", e)
                return None

            return wrapper

        return decorator_http_error

    @classmethod
    def register_global_metrics(cls, component_id):
        def decorator_register_metrics_method(func):
            @wraps(func)  # Preserve function metadata
            def wrapper(self, *args, **kwargs):
                func_hash = generate_hash(func, *args, **kwargs)
                if func_hash not in self.reported_global_metrics:
                    if func(self, *args, **kwargs):
                        self.reported_global_metrics.append(func_hash)

            if component_id not in cls.registered_global_metric_methods:
                cls.registered_global_metric_methods[component_id] = []
            cls.registered_global_metric_methods[component_id].append(wrapper)
            return wrapper

        return decorator_register_metrics_method

    @classmethod
    def register_project_metrics(cls, component_id):
        def decorator_register_metrics_method(func):
            @wraps(func)  # Preserve function metadata
            def wrapper(self, *args, **kwargs):
                func_hash = generate_hash(func, *args, **kwargs)
                if func_hash not in self.reported_project_metrics:
                    if func(self, *args, **kwargs):
                        self.reported_project_metrics.append(func_hash)

            if component_id not in cls.registered_project_metric_methods:
                cls.registered_project_metric_methods[component_id] = []
            cls.registered_project_metric_methods[component_id].append(wrapper)
            return wrapper

        return decorator_register_metrics_method

    def __init__(self, check):
        self.check = check
        self.found_in_catalog = False
        self.reported_global_metrics = []
        self.reported_project_metrics = []
        self.check.log.debug("created `%s` component", self.ID.value)

    def start_report(self):
        self.found_in_catalog = False
        self.reported_global_metrics.clear()
        self.reported_project_metrics.clear()

    def finish_report(self, tags):
        if not self.found_in_catalog:
            self.check.service_check(self.SERVICE_CHECK, AgentCheck.UNKNOWN, tags=tags)

    def report_global_metrics(self, config, tags):
        if self.ID not in Component.registered_global_metric_methods:
            self.check.log.debug("`%s` component has not registered methods for global metrics", self.ID.value)
            return
        self.check.log.debug("reporting `%s` component global metrics", self.ID.value)
        if self.check.api.component_in_catalog(self.TYPES.value):
            self.found_in_catalog = True
            self.check.log.debug("`%s` component found in catalog", self.ID.value)
            for registered_method in Component.registered_global_metric_methods[self.ID]:
                registered_method(self, config, tags)
        else:
            self.check.log.debug("`%s` component not found in catalog", self.ID.value)

    def report_project_metrics(self, project, config, project_tags):
        if self.ID not in Component.registered_project_metric_methods:
            self.check.log.debug("`%s` component has not registered methods for project metrics", self.ID.value)
            return
        if self.check.api.component_in_catalog(self.TYPES.value):
            self.found_in_catalog = True
            self.check.log.debug("`%s` component found in catalog for project %s", self.ID.value, project['name'])
            for registered_method in Component.registered_project_metric_methods[self.ID]:
                registered_method(self, project['id'], project_tags, config)
        else:
            self.check.log.debug("`%s` component not found in catalog for project %s", self.ID.value, project['name'])
