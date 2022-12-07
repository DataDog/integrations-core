# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from botocore.config import Config


def construct_boto_config(boto_config, proxies=None):
    if boto_config.get('proxies'):
        # Proxy settings configured in the boto_config config option takes precedence
        return Config(**boto_config)
    elif proxies:
        boto_config["proxies"] = proxies
        return Config(**boto_config)

    return Config(**boto_config)
