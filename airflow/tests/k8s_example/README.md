
## Before



## Start

```bash
kubectl apply -f local-storage.yaml
kubectl apply -f pv.yaml

# Needed once 
# helm repo add datadog https://helm.datadoghq.com
# helm repo add stable https://kubernetes-charts.storage.googleapis.com/
# helm repo update

helm install datadog -f datadog_values.yaml datadog/datadog
helm install airflow -f airflow_values.yaml stable/airflow
```


## Using local Airflow code

You can override Airflow code using a local version:

```python

```
