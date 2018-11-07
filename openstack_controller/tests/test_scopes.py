# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import re
import time

import mock
import pytest
from six import iteritems

from . import common

from datadog_checks.openstack_controller.exceptions import IncompleteIdentity
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.scopes import (OpenStackProject, OpenStackScope)