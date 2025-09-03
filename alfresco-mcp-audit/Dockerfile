# ---- Build stage ------------------------------------------------------------
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /workspace

# Build-time args so you can pin a branch, tag, or commit
ENV GIT_URL="https://github.com/jottley/alfresco-mcp.git"
ENV MAVEN_ARGS="-DskipTests"

# Install git, clone only the requested ref (shallow), and build
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN git clone "${GIT_URL}" src
# Fix Maven build
COPY pom.xml src/pom.xml 
RUN cd src \
 && mvn -q -e -B -U ${MAVEN_ARGS} package

# Normalize jar path -> /workspace/app.jar
RUN JAR_PATH="$(ls -1 src/target/*.jar | head -n1)" \
 && test -n "$JAR_PATH" \
 && cp "$JAR_PATH" /workspace/app.jar

# ---- Runtime stage ----------------------------------------------------------
FROM eclipse-temurin:17-jre-jammy
ENV APP_HOME=/opt/app \
    JAVA_OPTS="" \
    APP_ARGS="--host 0.0.0.0 --port 8081"
WORKDIR ${APP_HOME}

# Unprivileged user
RUN useradd -r -u 10001 appuser

# Copy built artifact
COPY --from=build /workspace/app.jar ${APP_HOME}/app.jar

EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
CMD wget -q -O- http://127.0.0.1:8081/actuator/health | grep -q '"status":"UP"' || exit 1

USER appuser

ENTRYPOINT [ "sh", "-lc", "exec java $JAVA_OPTS -jar /opt/app/app.jar $APP_ARGS" ]
