# Multi-stage build to keep final image clean
FROM python:3.11-slim-bookworm

# Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CLARITY_JAR_PATH=clarity.jar
ENV JAVA_OPTS="-Xmx2G -Xms1G"

# Install System Dependencies (Java 17 Runtime + Utils)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    findutils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python Dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Project files
COPY . .

# Copy and set permissions for startup script
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Start Application via script
CMD ["/app/start.sh"]
