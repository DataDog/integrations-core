# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from .ntp import NtpCheck
from .__about__ import __version__

__all__ = ['NtpCheck', '__version__']
