# Deployment

The application repository builds images. The GitOps repository deploys them.

## Repositories

- App repo: `leave-app`
- GitOps repo: `gitops-leave-app`

## Argo CD

Apply the Argo CD application from:

```sh
kubectl apply -f argocd/application-leave-app.yaml
```

## Image and Promotion Versions

- `IMAGE_VERSION`: `x.x.x`
- `PROMOTE_VERSION`: `x.x`

Example:

- `1.4.7` becomes image version `1.4.7`
- `1.4.7` becomes promote version `1.4`

