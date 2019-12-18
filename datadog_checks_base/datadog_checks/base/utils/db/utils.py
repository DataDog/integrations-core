# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
SUBMISSION_METHODS = {'gauge', 'count', 'monotonic_count', 'rate', 'histogram', 'historate'}


def create_submission_transformer(submit_method):
    def get_transformer(name, _, **modifiers):
        def transformer(value, *_, **kwargs):
            kwargs.update(modifiers)
            submit_method(name, value, **kwargs)

        return transformer

    return get_transformer
