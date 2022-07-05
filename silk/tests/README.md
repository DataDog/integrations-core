## E2E Testing

By default, the Silk e2e testing environment is mocked via caddy. This means that the metrics and events being collected are static. 

Events emitted by caddy will be submitted with the timestamp of the mocked value, therefore new events will appear with the mocked timestamp. 