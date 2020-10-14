set -e

kubectl apply -f local-storage.yaml
kubectl apply -f pv.yaml
# kubectl apply -f pvc.yaml

# helm repo add datadog https://helm.datadoghq.com
# helm repo add stable https://kubernetes-charts.storage.googleapis.com/
# helm repo update


helm install datadog -f datadog_values.yaml datadog/datadog

sleep 5

helm install airflow -f airflow_values.yaml stable/airflow
