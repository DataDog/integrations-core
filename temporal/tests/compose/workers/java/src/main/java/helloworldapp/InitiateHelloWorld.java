// @@@SNIPSTART hello-world-project-template-java-workflow-initiator
package helloworldapp;

import io.temporal.client.WorkflowClient;
import io.temporal.client.WorkflowOptions;
import io.temporal.serviceclient.WorkflowServiceStubs;
import io.temporal.serviceclient.WorkflowServiceStubsOptions;

public class InitiateHelloWorld {

    public static void main(String[] args) throws Exception {
        WorkflowServiceStubs service = WorkflowServiceStubs.newInstance(WorkflowServiceStubsOptions.newBuilder().setTarget("temporal:7233").build());
        // WorkflowClient can be used to start, signal, query, cancel, and terminate Workflows.
        WorkflowClient client = WorkflowClient.newInstance(service);
        WorkflowOptions options = WorkflowOptions.newBuilder()
                .setTaskQueue(Shared.HELLO_WORLD_TASK_QUEUE)
                .build();
        // WorkflowStubs enable calls to methods as if the Workflow object is local, but actually perform an RPC.
        HelloWorldWorkflow workflow = client.newWorkflowStub(HelloWorldWorkflow.class, options);
        // Synchronously execute the Workflow and wait for the response.
        String greeting = workflow.getGreeting("World");
        System.out.println(greeting);
        System.exit(0);
    }
}
// @@@SNIPEND
