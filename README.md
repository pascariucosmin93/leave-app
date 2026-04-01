# Employee Leave Management

This repository now follows the same split used in `gaz`: application code and CI/CD live here, while the Kubernetes deployment chart lives in the separate GitOps repository `gitops-leave-app`.

## Structure

```text
backend/             # Flask API
frontend/            # Static UI served by NGINX
tests/               # Pytest suite
kube-security/       # optional security manifests
monitoring/          # Grafana and Prometheus assets
argocd/              # Argo CD Application manifests
.github/workflows/   # Build/test/promotion workflows
archive/             # Original flat layout kept for reference
```

## Versioning

- Image version remains `x.x.x`
- Promote version remains `x.x`

The workflow computes `PROMOTE_VERSION` from `IMAGE_VERSION` by keeping only the major and minor components.

## Exposure

- The application is exposed through a Kubernetes `LoadBalancer` service.
- The cluster advertises external service IPs through BGP.
- NGINX in the frontend container proxies `/api/*` to the backend service inside the cluster.

## GitOps Flow

1. Build backend and frontend images with version `x.x.x`
2. Update `gitops-leave-app/k8s/chart/values.yaml`
3. Keep `versions.image` as `x.x.x`
4. Keep `versions.promote` as `x.x`
5. Argo CD syncs the GitOps repository into Kubernetes

## Notes

- I did not push anything.
- The original root files were moved to `archive/original-flat-layout/`.
- The GitOps chart now lives in `/Users/cosmin.pascariu/Desktop/gitops-leave-app`.
