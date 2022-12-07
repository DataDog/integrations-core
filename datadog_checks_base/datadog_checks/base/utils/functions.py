# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def identity(obj, **kwargs):
    """
    https://en.wikipedia.org/wiki/Identity_function
    """
    return obj


def no_op(*args, **kwargs):
    """
    https://en.wikipedia.org/wiki/NOP_(code)
    """


def predicate(assertion):
    """
    https://en.wikipedia.org/wiki/Predicate_(mathematical_logic)
    """
    return return_true if bool(assertion) else return_false


def return_true(*args, **kwargs):
    return True


def return_false(*args, **kwargs):
    return False


def raise_exception(exception_class, *args, **kwargs):
    raise exception_class(*args, **kwargs)
