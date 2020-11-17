# Airflow with KubernetesExecutor

This is a sample/lab Kubernetes setup with the Datadog Agent and Airflow using KubernetesExecutor.
 
## Setup

```bash
helm repo add datadog https://helm.datadoghq.com
helm repo add stable https://charts.helm.sh/stable
helm repo update
```

Sim link dags to the specific absolute location, needed for `pv.yaml`:

```bash
# from current folder
ln -s `pwd`/dags /tmp/airflow_dags
```

## Start

```bash
kubectl apply -f local-storage.yaml
kubectl apply -f pv.yaml

helm install datadog -f datadog_values.yaml datadog/datadog
helm install airflow -f airflow_values.yaml stable/airflow
```

To access Airflow UI:
```bash
export POD_NAME=$(kubectl get pods --namespace default -l "component=web,app=airflow" -o jsonpath="{.items[0].metadata.name}")
echo http://127.0.0.1:8080
kubectl port-forward --namespace default $POD_NAME 8080:8080
```

## Clean Up

```bash
helm uninstall datadog
helm uninstall airflow

kubectl delete -f pv.yaml
kubectl delete -f local-storage.yaml
```

If the clean up hangs, you might need to:

```bash
kubectl patch pvc test-volume -p '{"metadata":{"finalizers": []}}' --type=merge
kubectl delete pods --all
```

## Useful commands

### Get DogStatsD stats

```bash
docker exec `docker ps | grep k8s_agent_datadog | rev | cut -d ' ' -f 1 | rev` agent dogstatsd-stats
```

Example output:

```bash
airflow.dag.loading_duration             | dag_file:tutorial    | 10         | 2020-10-14 10:35:22.3520601 +0000 UTC
airflow.dag.loading_duration             | dag_file:hello_world_sleep5 | 9          | 2020-10-14 10:35:22.352042 +0000 UTC
airflow.job.start                        | job_name:schedulerjob | 1          | 2020-10-14 10:34:37.0857417 +0000 UTC
```

### Get Datadog Agent logs

```bash
docker exec `docker ps | grep k8s_agent_datadog | rev | cut -d ' ' -f 1 | rev` tail -f /var/log/datadog/agent.log
```

### Get Airflow logs

```bash
docker logs -f `docker ps | grep airflow-scheduler | rev | cut -d ' ' -f 1 | rev`
```

## Using local Airflow code

You can override Airflow code using a local version by uncommenting following sections in `airflow_values.yaml`:

```yaml
airflow:
  extraVolumeMounts:
    - name: airflow-code
      mountPath: /home/airflow/.local/lib/python3.6/site-packages/airflow/airflow

  extraVolumes:
    - name: airflow-code
      hostPath:
         path: <PATH_AIRFLOW_LOCAL_AIRFLOW_CODE>/airflow
``` 
