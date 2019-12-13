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


def create_extra_transformer(column_transformer, source=None):
    # Every column transformer expects a value to be given but in the post-processing
    # phase the values are determined by references, so to avoid redefining every
    # transformer we just map the proper source to the value.
    if source:

        def call_transformer(sources, **kwargs):
            return column_transformer(sources[source], sources, **kwargs)

    # Extra transformers that call regular transformers will want to pass values directly.
    else:

        def call_transformer(sources, value, **kwargs):
            return column_transformer(value, sources, **kwargs)

    return call_transformer
