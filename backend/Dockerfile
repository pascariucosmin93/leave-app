FROM python:3.11-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apk upgrade --no-cache \
    && apk add --no-cache build-base libffi-dev

COPY requirements.txt ./
RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip setuptools wheel \
    && find "$VIRTUAL_ENV" \( -name 'pip*dist-info' -o -name 'setuptools*' -o -name 'wheel*' -o -name 'jaraco.*' \) -exec rm -rf {} +

FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apk upgrade --no-cache \
    && addgroup -S app && adduser -S -G app app

COPY --from=builder /opt/venv /opt/venv
COPY . .
RUN chown -R app:app /app /opt/venv

USER app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/healthz/live')"

CMD ["gunicorn", "-c", "gunicorn_conf.py", "app:app"]
