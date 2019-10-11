# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_hostname():
    return 'stubbed.hostname'


def log(*args, **kwargs):
    pass


def get_config(*args, **kwargs):
    return ''


def get_version():
    return '0.0.0'


def warning(msg, *args, **kwargs):
    pass


def error(msg, *args, **kwargs):
    pass


def debug(msg, *args, **kwargs):
    pass


def set_check_metadata(*args, **kwargs):
    pass


def set_external_tags(*args, **kwargs):
    pass


def tracemalloc_enabled(*args, **kwargs):
    return False
