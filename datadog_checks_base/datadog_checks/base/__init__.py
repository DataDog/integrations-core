# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import lazy_loader

__getattr__, __dir__, __all__ = lazy_loader.attach_stub(__name__, __file__)

if __getattr__('datadog_agent').get_config('use_boringssl'):
    import urllib3.contrib.pyopenssl

    urllib3.contrib.pyopenssl.inject_into_urllib3()
