To test an example Quarkus app that exposed metrics, we took the documented example from here:
https://github.com/quarkusio/quarkus-quickstarts/tree/1347e49b4441e43c3faac3b3953dd5e988af379b/micrometer-quickstart

We then used this StackOverflow post to write a Dockerfile that would build the app:
https://stackoverflow.com/a/75759520

We needed the following tweaks:

- Tweak `.dockerignore` to stop ignoring all files.
- Disable the step `RUN ./mvnw dependency:go-offline -B` in the Dockerfile.
