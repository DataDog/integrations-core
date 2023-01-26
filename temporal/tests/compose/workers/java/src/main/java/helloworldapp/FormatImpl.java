// @@@SNIPSTART hello-world-project-template-java-activity
package helloworldapp;

public class FormatImpl implements Format {

    @Override
    public String composeGreeting(String name) {
        return "Hello " + name + "!";
    }
}
// @@@SNIPEND
