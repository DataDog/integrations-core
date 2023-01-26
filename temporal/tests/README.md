# How to run the workflows

## Golang

```commandline
docker exec temporal-admin-tools tctl workflow start --taskqueue go-task-queue --workflow_type GreetingWorkflow --input '"world"'
```

## Python

```commandline
docker exec temporal-admin-tools tctl workflow start --taskqueue python-task-queue --workflow_type SayHello --input '"world"'
```

## Java
```commandline
docker exec temporal-admin-tools tctl workflow start --taskqueue java-task-queue --workflow_type HelloWorldWorkflow --input '"world"'
```
