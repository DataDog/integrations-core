CHECK_NAME = 'teamcity'

CONFIG = {
    'instances': [
        {
            'name': 'One test build',
            'server': 'localhost:8111',
            'build_configuration': 'TestProject_TestBuild',
            'host_affected': 'buildhost42.dtdg.co',
            'basic_http_authentication': False,
            'is_deployment': False,
            'tags': ['one:tag', 'one:test'],
        }
    ]
}
