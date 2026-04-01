FROM nginx:1.29.2-alpine

RUN apk update && apk upgrade --no-cache

WORKDIR /usr/share/nginx/html

# Copy the frontend assets (HTML, CSS, JS) into the container.
COPY . /usr/share/nginx/html

# Replace the default NGINX config with the custom one.
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
