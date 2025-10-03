FROM openjdk:11-jre-slim

LABEL maintainer="CI/CD Demo Team"
LABEL description="CI/CD Pipeline Demo with Terraform"

# Create app directory
WORKDIR /app

# Copy the JAR file
COPY target/ci-cd-demo.jar app.jar

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
ENTRYPOINT ["java", "-jar", "app.jar"]