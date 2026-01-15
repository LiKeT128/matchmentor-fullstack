# Multi-stage build for OpenDota parser
FROM maven:3.9-eclipse-temurin-21 AS parser-builder

WORKDIR /parser
COPY odota-parser /parser
RUN mvn clean install -DskipTests

# Main application image
FROM python:3.11-slim-bookworm

# Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PARSER_PORT=5600
ENV PARSER_JAR_PATH=parser.jar

# Install System Dependencies (Java 21 Runtime for parser)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    findutils \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy parser JAR from builder stage
COPY --from=parser-builder /parser/target/stats-0.1.0.jar ./parser.jar

# Install Python Dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Project files
COPY . .

# Copy and set permissions for startup script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Create temp demos directory
RUN mkdir -p /tmp/demos

# Expose ports
EXPOSE 8080 5600

# Start Application via script (which starts both parser and FastAPI)
CMD ["/app/start.sh"]

