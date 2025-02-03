# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import os

from datadog_checks.dev.fs import get_here

USE_OCTOPUS_LAB = os.environ.get("USE_OCTOPUS_LAB")
OCTOPUS_LAB_ENDPOINT = os.environ.get('OCTOPUS_LAB_ENDPOINT')
OCTOPUS_API_KEY = os.environ.get('OCTOPUS_API_KEY')
OCTOPUS_SPACE = os.environ.get('OCTOPUS_SPACE', 'Default')

COMPOSE_FILE = os.path.join(get_here(), 'docker', 'docker-compose.yaml')
INSTANCE = {'octopus_endpoint': 'http://localhost:80'}

LAB_INSTANCE = {
    'octopus_endpoint': OCTOPUS_LAB_ENDPOINT,
    'headers': {'X-Octopus-ApiKey': OCTOPUS_API_KEY},
}

DEFAULT_COLLECTION_INTERVAL = 15
MOCKED_TIME1 = datetime.datetime.fromisoformat("2024-09-23T14:45:00.123+00:00")
MOCKED_TIME2 = MOCKED_TIME1 + datetime.timedelta(seconds=DEFAULT_COLLECTION_INTERVAL)


DEPLOY_METRICS = [
    "octopus_deploy.deployment.count",
    "octopus_deploy.deployment.executing",
    "octopus_deploy.deployment.queued",
    "octopus_deploy.deployment.waiting",
    "octopus_deploy.deployment.queued_time",
    "octopus_deploy.deployment.executing_time",
    "octopus_deploy.deployment.completed_time",
]

MACHINE_METRICS = [
    "octopus_deploy.machine.count",
    "octopus_deploy.machine.is_healthy",
]

SPACE_METRICS = [
    "octopus_deploy.space.count",
]

PROJECT_GROUP_METRICS = [
    "octopus_deploy.project_group.count",
]

PROJECT_METRICS = [
    "octopus_deploy.project.count",
]

ENV_METRICS = [
    "octopus_deploy.environment.allow_dynamic_infrastructure",
    "octopus_deploy.environment.count",
    "octopus_deploy.environment.use_guided_failure",
]

SERVER_METRICS = [
    "octopus_deploy.server_node.count",
    "octopus_deploy.server_node.in_maintenance_mode",
    "octopus_deploy.server_node.max_concurrent_tasks",
]

COMPLETED_METRICS = ["octopus_deploy.deployment.completed_time"]

ALL_METRICS = (
    SERVER_METRICS
    + ENV_METRICS
    + PROJECT_METRICS
    + PROJECT_GROUP_METRICS
    + MACHINE_METRICS
    + SPACE_METRICS
    + DEPLOY_METRICS
)

ALL_DEPLOYMENT_LOGS = [
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The deployment failed because one or more steps failed. Please see the deployment log for details.',
        'timestamp': 1727104203218,
        'status': 'Fatal',
        'stage_name': 'Deploy test release 0.0.2 to Development',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'hello',
        'timestamp': 1727104198525,
        'status': 'Info',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': "The step failed: Activity Run a Script on the Octopus Server failed with error "
        "'The remote script failed with exit code 1'.",
        'timestamp': 1727104202767,
        'status': 'Fatal',
        'stage_name': 'Step 2: Run a Script',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'ParserError: At /home/octopus/.octopus/OctopusServer/Server/Work/'
        '09234928998123-1847-68/Script.ps1:1 char:6',
        'timestamp': 1727104202599,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': '+ echo "stop',
        'timestamp': 1727104202599,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': '+      ~~~~~',
        'timestamp': 1727104202599,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The string is missing the terminator: ".',
        'timestamp': 1727104202599,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'At /home/octopus/.octopus/OctopusServer/Server/Work/09234928998123-1847-68/Script.ps1:1 char:6',
        'timestamp': 1727104202605,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': '+ echo "stop',
        'timestamp': 1727104202605,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': '+      ~~~~~',
        'timestamp': 1727104202605,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, <No file>: line 1',
        'timestamp': 1727104202606,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, /home/octopus/.octopus/OctopusServer/Server/Work/'
        '09234928998123-1847-68/Octopus.FunctionAppenderContext.ps1: line 258',
        'timestamp': 1727104202606,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, /home/octopus/.octopus/OctopusServer/Server/Work/'
        '09234928998123-1847-68/Bootstrap.Octopus.FunctionAppenderContext.ps1: line 1505',
        'timestamp': 1727104202607,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, <No file>: line 1',
        'timestamp': 1727104202607,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, <No file>: line 1',
        'timestamp': 1727104202607,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The remote script failed with exit code 1',
        'timestamp': 1727104202733,
        'status': 'Fatal',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The action Run a Script on the Octopus Server failed',
        'timestamp': 1727104202758,
        'status': 'Fatal',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-18,release_version:0.0.1,environment_name:staging,'
        'space_name:Default,project_name:test,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The deployment completed successfully.',
        'timestamp': 1727103628255,
        'status': 'Info',
        'stage_name': 'Deploy test release 0.0.1 to Staging',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-18,release_version:0.0.1,environment_name:staging,'
        'space_name:Default,project_name:test,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'hello',
        'timestamp': 1727103627639,
        'status': 'Info',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-17,release_version:0.0.1,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The deployment completed successfully.',
        'timestamp': 1727103621669,
        'status': 'Info',
        'stage_name': 'Deploy test release 0.0.1 to Development',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-17,release_version:0.0.1,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'hello',
        'timestamp': 1727103621208,
        'status': 'Info',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-16,release_version:0.1.5,environment_name:dev,'
        'space_name:Default,project_name:test-api,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The deployment completed successfully.',
        'timestamp': 1727103442532,
        'status': 'Info',
        'stage_name': 'Deploy test-api release 0.1.5 to Development',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-16,release_version:0.1.5,environment_name:dev,'
        'space_name:Default,project_name:test-api,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'Testing',
        'timestamp': 1727103440967,
        'status': 'Info',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-16,release_version:0.1.5,environment_name:dev,'
        'space_name:Default,project_name:test-api,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'test',
        'timestamp': 1727103442029,
        'status': 'Info',
        'stage_name': 'Octopus Server',
    },
]

ONLY_TEST_LOGS = [
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The deployment failed because one or more steps failed. Please see the deployment log for details.',
        'timestamp': 1727104203218,
        'status': 'Fatal',
        'stage_name': 'Deploy test release 0.0.2 to Development',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'hello',
        'timestamp': 1727104198525,
        'status': 'Info',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': "The step failed: Activity Run a Script on the Octopus Server failed with error"
        " 'The remote script failed with exit code 1'.",
        'timestamp': 1727104202767,
        'status': 'Fatal',
        'stage_name': 'Step 2: Run a Script',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'ParserError: At /home/octopus/.octopus/OctopusServer/Server/Work/'
        '09234928998123-1847-68/Script.ps1:1 char:6',
        'timestamp': 1727104202599,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': '+ echo "stop',
        'timestamp': 1727104202599,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': '+      ~~~~~',
        'timestamp': 1727104202599,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The string is missing the terminator: ".',
        'timestamp': 1727104202599,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'At /home/octopus/.octopus/OctopusServer/Server/Work/' '09234928998123-1847-68/Script.ps1:1 char:6',
        'timestamp': 1727104202605,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': '+ echo "stop',
        'timestamp': 1727104202605,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': '+      ~~~~~',
        'timestamp': 1727104202605,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, <No file>: line 1',
        'timestamp': 1727104202606,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, /home/octopus/.octopus/OctopusServer/Server/Work/'
        '09234928998123-1847-68/Octopus.FunctionAppenderContext.ps1: line 258',
        'timestamp': 1727104202606,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, /home/octopus/.octopus/OctopusServer/Server/Work/'
        '09234928998123-1847-68/Bootstrap.Octopus.FunctionAppenderContext.ps1: line 1505',
        'timestamp': 1727104202607,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, <No file>: line 1',
        'timestamp': 1727104202607,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'at <ScriptBlock>, <No file>: line 1',
        'timestamp': 1727104202607,
        'status': 'Error',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The remote script failed with exit code 1',
        'timestamp': 1727104202733,
        'status': 'Fatal',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-19,release_version:0.0.2,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Failed,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The action Run a Script on the Octopus Server failed',
        'timestamp': 1727104202758,
        'status': 'Fatal',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-18,release_version:0.0.1,environment_name:staging,'
        'space_name:Default,project_name:test,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The deployment completed successfully.',
        'timestamp': 1727103628255,
        'status': 'Info',
        'stage_name': 'Deploy test release 0.0.1 to Staging',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-18,release_version:0.0.1,environment_name:staging,'
        'space_name:Default,project_name:test,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'hello',
        'timestamp': 1727103627639,
        'status': 'Info',
        'stage_name': 'Octopus Server',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-17,release_version:0.0.1,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'The deployment completed successfully.',
        'timestamp': 1727103621669,
        'status': 'Info',
        'stage_name': 'Deploy test release 0.0.1 to Development',
    },
    {
        'ddtags': 'octopus_server:http://localhost:80,deployment_id:Deployments-17,release_version:0.0.1,environment_name:dev,'
        'space_name:Default,project_name:test,task_state:Success,'
        'server_node:OctopusServerNodes-50c3dfbarc82',
        'message': 'hello',
        'timestamp': 1727103621208,
        'status': 'Info',
        'stage_name': 'Octopus Server',
    },
]

ALL_EVENTS = [
    {
        'message': 'Machine test is unhealthy',
        'tags': ['octopus_server:http://localhost:80', 'space_name:Default'],
    },
    {
        'message': 'Deploy to dev failed for new-project-from-group release 0.0.2 to dev',
        'tags': ['octopus_server:http://localhost:80', 'space_name:Default'],
    },
    {
        'message': 'Deploy to dev failed for project-new-2 release 0.0.2 to dev',
        'tags': ['octopus_server:http://localhost:80', 'space_name:Default'],
    },
]
