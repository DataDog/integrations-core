# Airflow Dev Readme

## Testing Airflow StatsD emitter with Agent DogStatsD

/!\ Works only on Linux. Docker `network_mode` only works as expected on Linux.

On a machine/VM with the desired Agent version installed and DogStatsD activated (enabled by default).

```

# 1a. Copy the `dogstatsd_mapper_profiles` mappings from the main readme.md to main `datadog.yaml`
# 1b. Also set `dogstatsd_metrics_stats_enable=true` in main `datadog.yaml`
# 1c. Restart Agent

# 2. Set `network_mode: host` in airflow/tests/compose/docker-compose.yaml

# 3. Start airflow

docker-compose -f airflow/tests/compose/docker-compose.yaml up

# 4. Check the agent is receiving the airflow statsd metrics

sudo -u dd-agent datadog-agent dogstatsd-stats
```
