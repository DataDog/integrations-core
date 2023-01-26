FROM gradle:jdk17-jammy
COPY --chown=gradle:gradle . /app
WORKDIR /app
RUN ./gradlew build

ENTRYPOINT ["./gradlew", "startWorker"]
