FROM nginxinc/nginx-unprivileged:1.29-alpine

USER root
RUN apk update && apk upgrade --no-cache

WORKDIR /usr/share/nginx/html

# Copy only the frontend assets served by nginx.
COPY public/ /usr/share/nginx/html/

# Replace the default NGINX config with the custom one.
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

USER 101

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
