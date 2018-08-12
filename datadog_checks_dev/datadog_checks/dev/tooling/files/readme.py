# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from .utils import File

TEMPLATE = """\
# Agent Check: {name_cap}
## Overview

This check monitors [{name_cap}][1].

## Setup

### Installation

The {name_cap} check is included in the [Datadog Agent][2] package, so you don't
need to install anything else on your server.

### Configuration

1. Edit the `{name}.d/conf.yaml` file, in the `conf.d/` folder at the root of your
  Agent's configuration directory to start collecting your {name} performance data.
  See the [sample {name}.d/conf.yaml][3] for all available configuration options.

2. [Restart the Agent][4]

### Validation

[Run the Agent's `status` subcommand][5] and look for `{name}` under the Checks section.

## Data Collected
### Metrics

The {name_cap} check does not include any metrics at this time.

### Service Checks

The {name_cap} check does not include any service checks at this time.

### Events

The {name_cap} check does not include any events at this time.

## Troubleshooting

Need help? Contact [Datadog Support][6].

[1]: link to integration's site
[2]: https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/{name}/datadog_checks/{name}/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/faq/agent-commands/#start-stop-restart-the-agent
[5]: https://docs.datadoghq.com/agent/faq/agent-commands/#agent-status-and-information
[6]: https://docs.datadoghq.com/help/
"""


class Readme(File):
    def __init__(self, config):
        super(Readme, self).__init__(
            os.path.join(config['root'], 'README.md'),
            TEMPLATE.format(
                name=config['check_name'],
                name_cap=config['check_name_cap'],
            )
        )
