# How to run the workflows

## Python

```commandline
docker exec temporal-admin-tools tctl workflow start --taskqueue python-task-queue --workflow_type SayHello --input '"world"'
```