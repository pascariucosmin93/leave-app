FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl gnupg && \
    curl -sLO "https://dl.k8s.io/release/$(curl -sL https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm -f kubectl && \
    pip install --no-cache-dir requests && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY cleanup_blocked_ips_notifications.py /app/cleanup_blocked_ips_notifications.py

ENTRYPOINT ["python3", "/app/cleanup_blocked_ips_notifications.py"]

