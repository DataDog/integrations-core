# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys

if __name__ == "__main__":
    mock_output = sys.argv[1]
    print('fluentd {}'.format(mock_output))
