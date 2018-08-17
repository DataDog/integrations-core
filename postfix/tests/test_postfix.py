# stdlib
import binascii
import logging
import os
from random import sample, shuffle
import re
import shutil
import unittest

import pytest

log = logging.getLogger()


@pytest.fixture
def setup():
    
