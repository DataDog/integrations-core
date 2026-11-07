# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import lazy_loader

from .utils._certificate_distrust import install as _install_certificate_distrust

__getattr__, __dir__, __all__ = lazy_loader.attach_stub(__name__, __file__)

# Every check imports this package, so this makes the TLS connections of every integration in the process reject
# distrusted CA keys, including those that build their own contexts or trust certifi's bundle.
_install_certificate_distrust()

if __getattr__('datadog_agent').get_config('use_boringssl'):
    import urllib3.contrib.pyopenssl

    urllib3.contrib.pyopenssl.inject_into_urllib3()
