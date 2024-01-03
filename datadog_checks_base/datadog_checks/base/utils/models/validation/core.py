# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def initialize_config(values, **kwargs):
    # This is what is returned by the initial model validator of each config model.
    return values


def check_model(model, **kwargs):
    # This is what is returned by the final model validator of each config model.
    return model
