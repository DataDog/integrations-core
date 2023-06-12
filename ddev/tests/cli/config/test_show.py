# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os


def test_default_scrubbed(ddev, config_file, helpers):
    config_file.model.orgs['default']['api_key'] = 'foo'
    config_file.model.orgs['default']['app_key'] = 'bar'
    config_file.model.github = {'user': '', 'token': ''}
    config_file.save()

    result = ddev('config', 'show')

    sep = os.sep.replace('\\', '\\\\')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        repo = "core"
        agent = "dev"
        org = "default"

        [repos]
        core = "~{sep}dd{sep}integrations-core"
        extras = "~{sep}dd{sep}integrations-extras"
        marketplace = "~{sep}dd{sep}marketplace"
        agent = "~{sep}dd{sep}datadog-agent"

        [agents.dev]
        docker = "datadog/agent-dev:master"
        local = "latest"

        [agents.7]
        docker = "datadog/agent:7"
        local = "7"

        [orgs.default]
        api_key = "*****"
        app_key = "*****"
        site = "datadoghq.com"
        dd_url = "https://app.datadoghq.com"
        log_url = ""

        [github]
        user = ""
        token = "*****"

        [pypi]
        user = ""
        auth = "*****"

        [trello]
        key = ""
        token = "*****"

        [terminal.styles]
        info = "bold"
        success = "bold cyan"
        error = "bold red"
        warning = "bold yellow"
        waiting = "bold magenta"
        debug = "bold"
        spinner = "simpleDotsScrolling"
        """
    )


def test_reveal(ddev, config_file, helpers):
    config_file.model.orgs['default']['api_key'] = 'foo'
    config_file.model.orgs['default']['app_key'] = 'bar'
    config_file.model.github = {'user': '', 'token': ''}
    config_file.save()

    result = ddev('config', 'show', '-a')

    sep = os.sep.replace('\\', '\\\\')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        repo = "core"
        agent = "dev"
        org = "default"

        [repos]
        core = "~{sep}dd{sep}integrations-core"
        extras = "~{sep}dd{sep}integrations-extras"
        marketplace = "~{sep}dd{sep}marketplace"
        agent = "~{sep}dd{sep}datadog-agent"

        [agents.dev]
        docker = "datadog/agent-dev:master"
        local = "latest"

        [agents.7]
        docker = "datadog/agent:7"
        local = "7"

        [orgs.default]
        api_key = "foo"
        app_key = "bar"
        site = "datadoghq.com"
        dd_url = "https://app.datadoghq.com"
        log_url = ""

        [github]
        user = ""
        token = ""

        [pypi]
        user = ""
        auth = ""

        [trello]
        key = ""
        token = ""

        [terminal.styles]
        info = "bold"
        success = "bold cyan"
        error = "bold red"
        warning = "bold yellow"
        waiting = "bold magenta"
        debug = "bold"
        spinner = "simpleDotsScrolling"
        """
    )
