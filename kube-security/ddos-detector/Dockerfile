# Start from Python with kubectl preinstalled via apt
FROM python:3.11-slim

WORKDIR /app

# Install dependencies: curl + kubectl + requests
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -sLO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm -f kubectl && \
    pip install --no-cache-dir requests && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy detection script
COPY detect_ddos_loki_notifications.py /app/detect_ddos_loki_notifications.py

ENTRYPOINT ["python3", "/app/detect_ddos_loki_notifications.py"]
