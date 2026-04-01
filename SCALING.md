# Technical Documentation

This repository contains the application layer of the leave management platform: backend, frontend, Helm chart, monitoring assets, and Kubernetes security jobs.

For the current operational entry points, use:

- `README.md` for the project overview
- `docs/DEPLOYMENT.md` for deployment steps
- `docs/SCALING.md` for autoscaling and HA notes

## Scope

The platform includes:

- Flask backend with MySQL integration
- Static frontend served by NGINX
- Helm chart for Kubernetes deployment
- Prometheus, Grafana, and Loki integration assets
- Discord-based operational notifications
- Kubernetes security jobs for DDoS detection and cleanup

## Compatibility Note

The project naming is now aligned as follows: project `employee-leave-management`, namespace/release `employee-leave`, and images `employee-leave-backend` / `employee-leave-frontend`. Some historical dashboard labels may still need cleanup.
