# Airflow Dev Readme

## Manual testing Airflow StatsD emitter with Agent DogStatsD Mapper

/!\ Works only on Linux. Docker `network_mode` only works as expected on Linux.

### 1. Start airflow

Example:

```bash
ddev env start airflow py38
```

### 2. Check the agent is receiving the airflow statsd metrics

```bash
docker exec -it dd_airflow_py38 agent dogstatsd-stats
```

### TODO: Create e2e testing assertions for DogStatsD metrics instead of manual checking the result.
