helm uninstall datadog
helm uninstall airflow

kubectl patch pvc test-volume -p '{"metadata":{"finalizers": []}}' --type=merge
sleep 1
kubectl delete -f pv.yaml
kubectl delete -f local-storage.yaml

