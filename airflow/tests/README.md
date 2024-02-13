# Airflow Dev Readme

## Manual testing Airflow StatsD emitter with Agent DogStatsD Mapper
/!\ Works only on Linux. Docker `network_mode` only works as expected on Linux.

### 1. Start airflow

Example:

```bash
ddev env start airflow py39
```

### 2. Check the agent is receiving the airflow statsd metrics

```bash
docker exec -it dd_airflow_py39 agent dogstatsd-stats
```

# Airflow REST API metrics

## Triggering the DAG Task
```bash
ddev env start airflow py3.11-2.6
```
Go to localhost:8080/login and enter admin credentials.

### Manually trigger the DAG run via the UI
Trigger the dag to start DagRun and move it to a running state.

### Run agent manual check
View the generated `airflow.dag.task.ongoing_duration` via the manual check run
```bash
ddev env agent airflow py3.11-2.6 check
```
