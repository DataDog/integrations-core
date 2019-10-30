
https://medium.com/@andreyonistchuk/how-to-run-spark-2-4-on-osx-minikube-f0e5fdeb27be


```
; ./bin/spark-submit \
--master k8s://https://192.168.99.100:8443 \
--deploy-mode cluster \
--name spark-pi \
--class org.apache.spark.examples.SparkPi \
--conf spark.executor.instances=2 --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark \
--conf spark.kubernetes.container.image=spark:spark \
local:///opt/spark/examples/jars/spark-examples_2.11-2.4.4.jar 1000000
```

```

RUN rm $SPARK_HOME/jars/kubernetes-client-*.jar
ADD https://repo1.maven.org/maven2/io/fabric8/kubernetes-client/4.4.2/kubernetes-client-4.4.2.jar $SPARK_HOME/jars

```