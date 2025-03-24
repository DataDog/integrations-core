# (C) Datadog, Inc. 2016-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import lazy_loader

__getattr__, __dir__, __all__ = lazy_loader.attach_stub(__name__, __file__)
