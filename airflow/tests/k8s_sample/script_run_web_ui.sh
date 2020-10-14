export POD_NAME=$(kubectl get pods --namespace default -l "component=web,app=airflow" -o jsonpath="{.items[0].metadata.name}")
echo http://127.0.0.1:8080
kubectl port-forward --namespace default $POD_NAME 8080:8080