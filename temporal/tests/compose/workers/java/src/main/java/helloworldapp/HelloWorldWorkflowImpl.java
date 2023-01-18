// @@@SNIPSTART hello-world-project-template-java-workflow
package helloworldapp;

import io.temporal.activity.ActivityOptions;
import io.temporal.workflow.Workflow;

import java.time.Duration;

public class HelloWorldWorkflowImpl implements HelloWorldWorkflow {

    ActivityOptions options = ActivityOptions.newBuilder()
            .setScheduleToCloseTimeout(Duration.ofSeconds(2))
            .build();

    // ActivityStubs enable calls to Activities as if they are local methods, but actually perform an RPC.
    private final Format format = Workflow.newActivityStub(Format.class, options);

    @Override
    public String getGreeting(String name) {
        // This is the entry point to the Workflow.
        // If there were other Activity methods they would be orchestrated here or from within other Activities.
        return format.composeGreeting(name);
    }
}
// @@@SNIPEND
