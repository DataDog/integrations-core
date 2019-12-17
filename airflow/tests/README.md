# Airflow Dev Readme

## Testing Airflow Statsd emitter with Agent Dogstatsd

On a machine/vm with the desired agent version installed and Dogstatsd activated (enabled by default).

```
pip install apache-airflow
pip install 'apache-airflow[statsd]'

# airflow needs a home, ~/airflow is the default,
# but you can lay foundation somewhere else if you prefer
# (optional)
export AIRFLOW_HOME=~/airflow

# install from pypi using pip
pip install apache-airflow

# initialize the database
airflow initdb

# enable statsd
Set `statsd_on = True` in `~/airflow/airflow.cfg`

# copy the `dogstatsd_mapper_profiles` mappings from the main readme.md to `/etc/datadog/datadog.yaml`

# start the web server, default port is 8080
airflow webserver -p 8080

# check the agent is receiving the airflow statsd metrics
sudo -u dd-agent datadog-agent dogstatsd-stats
```
