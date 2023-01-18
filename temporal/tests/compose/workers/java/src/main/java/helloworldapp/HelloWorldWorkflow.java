// @@@SNIPSTART hello-world-project-template-java-workflow-interface
package helloworldapp;

import io.temporal.workflow.WorkflowInterface;
import io.temporal.workflow.WorkflowMethod;

@WorkflowInterface
public interface HelloWorldWorkflow {

    @WorkflowMethod
    String getGreeting(String name);
}
// @@@SNIPEND
