# E2E Testing with Logs

The default E2E configuration utilizes log aggregation to the `historyserver` which makes it difficult to extract the logs to test or implement logs ingestion.  It remains the default configuration since it does not leave any extra files after the environment is stopped.

To test logs ingestion with the Agent, make the following changes to instead log the files locally via a mapped volume within the container, and also make them accesible to the agent.

1. First, comment out the aggregation flags from the env file:

        +++ b/mapreduce/tests/compose/hadoop.env

        -YARN_CONF_yarn_log___aggregation___enable=true
        -YARN_CONF_yarn_log_server_url=http://historyserver:8188/applicationhistory/logs/
        +#YARN_CONF_yarn_log___aggregation___enable=true
        +#YARN_CONF_yarn_log_server_url=http://historyserver:8188/applicationhistory/logs/

2. Next, map that directory to the local filesystem from the `nodemanager1` node:

        +++ b/mapreduce/tests/compose/docker-compose.yaml
        @@ -55,6 +55,8 @@ services:
               - ./hadoop.env
             networks:
               - hadoop_net
        +    volumes:
        +      - ./userlogs/:/opt/hadoop-3.2.1/logs/userlogs

3. Tell the agent container to mount the same directory:

        diff --git a/mapreduce/tests/conftest.py b/mapreduce/tests/conftest.py
        +++ b/mapreduce/tests/conftest.py
        @@ -37,7 +37,9 @@ def dd_environment():
                 env_vars=env,
             ):
                 # 'custom_hosts' in metadata provides native /etc/hosts mappings in the agent's docker container
        -        yield INSTANCE_INTEGRATION, {'custom_hosts': get_custom_hosts()}
        +
        +        yield INSTANCE_INTEGRATION, {'custom_hosts': get_custom_hosts(),
        +                                     'docker_volumes': ['ABSOLUTE_PATH_TO_REPO/integrations-core/mapreduce/tests/compose/userlogs:/var/log/mapreduce/userlogs']}

4. Finally, after the environment has been loaded, update the `mapreduce.yaml` config in the Agent container with the following logs configuration:

        logs:
        - path: /var/log/mapreduce/userlogs/*/*/syslog
          service: mapreduce
          source: mapreduce
          type: file
          log_processing_rules:
            - type: multi_line
              pattern: \d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2},\d{3}
              name: new_log_start_with_date
        - path: /var/log/mapreduce/userlogs/*/*/stderr
          service: mapreduce
          source: mapreduce
          type: file
          log_processing_rules:
            - type: multi_line
              pattern: \d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2},\d{3}
              name: new_log_start_with_date
        - path: /var/log/mapreduce/userlogs/*/*/stdout
          service: mapreduce
          source: mapreduce
          type: file
          log_processing_rules:
            - type: multi_line
              pattern: \d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2},\d{3}
              name: new_log_start_with_date
