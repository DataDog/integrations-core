# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_hostname():
    return b'stubbed.hostname'


def log(*args, **kwargs):
    pass


def get_config(*args, **kwargs):
    return ""

def warning(msg, *args, **kwargs):
    pass

def error(msg, *args, **kwargs):
    pass

def debug(msg, *args, **kwargs):
    pass
