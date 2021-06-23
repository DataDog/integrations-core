# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy


def get_metadata(check, metric_name, modifiers, global_options):
    """
    This allows for the submission of instance metadata like a product's version. The required modifier
    `label` indicates which label contains the desired information. For more information, see:
    https://datadoghq.dev/integrations-core/base/metadata/
    """
    set_metadata_method = check.set_metadata

    options = deepcopy(modifiers)
    label = options.pop('label', '')
    if not isinstance(label, str):
        raise TypeError('the `label` parameter must be a string')
    elif not label:
        raise ValueError('the `label` parameter is required')

    def metadata(metric, sample_data, runtime_data):
        for sample, _tags, _hostname in sample_data:
            set_metadata_method(metric_name, sample.labels[label], **options)

    del check
    del modifiers
    del global_options
    return metadata
