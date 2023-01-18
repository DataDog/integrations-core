# How to run the workflows

## Golang

```commandline
docker exec temporal-admin-tools tctl workflow start --taskqueue go-task-queue --workflow_type GreetingWorkflow --input '"world"'
```
