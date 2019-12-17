# Airflow Dev Readme

## Testing Airflow Statsd emitter with Agent Dogstatsd

On a machine/vm with the desired agent version installed and Dogstatsd activated (enabled by default).

```

# 1. Copy the `dogstatsd_mapper_profiles` mappings from the main readme.md to `/etc/datadog/datadog.yaml`

# 2. Set `network_mode: host` in airflow/tests/compose/docker-compose.yaml

# 3. Start airflow

docker-compose -f airflow/tests/compose/docker-compose.yaml up

# 4. Check the agent is receiving the airflow statsd metrics

sudo -u dd-agent datadog-agent dogstatsd-stats
```
