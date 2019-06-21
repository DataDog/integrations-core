# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from .__about__ import __version__
from .ntp import NtpCheck

__all__ = ['NtpCheck', '__version__']
