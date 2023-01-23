// @@@SNIPSTART hello-world-project-template-java-worker
package helloworldapp;

import static java.nio.charset.StandardCharsets.UTF_8;

import com.sun.net.httpserver.HttpServer;
import com.uber.m3.tally.RootScopeBuilder;
import com.uber.m3.tally.Scope;
import io.micrometer.prometheus.PrometheusConfig;
import io.micrometer.prometheus.PrometheusMeterRegistry;
import io.temporal.client.WorkflowClient;
import io.temporal.common.reporter.MicrometerClientStatsReporter;
import io.temporal.serviceclient.WorkflowServiceStubs;
import io.temporal.serviceclient.WorkflowServiceStubsOptions;
import io.temporal.worker.Worker;
import io.temporal.worker.WorkerFactory;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;

public class HelloWorldWorker {

  public static void main(String[] args) {

    // Set up prometheus registry and stats reported
    PrometheusMeterRegistry registry = new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);
    // Set up a new scope, report every 1 second
    Scope scope =
        new RootScopeBuilder()
            .reporter(new MicrometerClientStatsReporter(registry))
            .reportEvery(com.uber.m3.util.Duration.ofSeconds(1));
    // Start the prometheus scrape endpoint
    HttpServer scrapeEndpoint = HelloWorldWorker.startPrometheusScrapeEndpoint(registry, 8080);
    // Stopping the worker will stop the http server that exposes the
    // scrape endpoint.
    Runtime.getRuntime().addShutdownHook(new Thread(() -> scrapeEndpoint.stop(1)));
    // Add metrics scope to workflow service stub options
    WorkflowServiceStubsOptions stubOptions =
        WorkflowServiceStubsOptions.newBuilder().setMetricsScope(scope).setTarget("temporal:7233").build();

    WorkflowServiceStubs service = WorkflowServiceStubs.newServiceStubs(stubOptions);
    WorkflowClient client = WorkflowClient.newInstance(service);
    WorkerFactory factory = WorkerFactory.newInstance(client);

    Worker worker = factory.newWorker(Shared.HELLO_WORLD_TASK_QUEUE);
    // This Worker hosts both Workflow and Activity implementations.
    // Workflows are stateful, so you need to supply a type to create instances.
    worker.registerWorkflowImplementationTypes(HelloWorldWorkflowImpl.class);
    // Activities are stateless and thread safe, so a shared instance is used.
    worker.registerActivitiesImplementations(new FormatImpl());

    factory.start();

  }

      /**
       * Starts HttpServer to expose a scrape endpoint. See
       * https://micrometer.io/docs/registry/prometheus for more info.
       */
      public static HttpServer startPrometheusScrapeEndpoint(
          PrometheusMeterRegistry registry, int port) {
        try {
          HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
          server.createContext(
              "/metrics",
              httpExchange -> {
                String response = registry.scrape();
                httpExchange.sendResponseHeaders(200, response.getBytes(UTF_8).length);
                try (OutputStream os = httpExchange.getResponseBody()) {
                  os.write(response.getBytes(UTF_8));
                }
              });

          server.start();
          return server;
        } catch (IOException e) {
          throw new RuntimeException(e);
        }
      }
}
// @@@SNIPEND
