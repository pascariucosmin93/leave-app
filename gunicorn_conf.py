name: Build, Push, Scan and Deploy

permissions:
  contents: read
  actions: write

on:
  push:
    branches:
      - main

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install pytest pytest-cov flake8 bandit safety
          mkdir -p reports

      - name: Run flake8
        run: flake8 backend --count --statistics || true

      - name: Run Bandit
        run: bandit -r backend -f txt -o reports/bandit-report.txt || true

      - name: Run Safety
        run: safety check --file backend/requirements.txt --output text > reports/safety-report.txt || true

      - name: Run unit tests
        env:
          UNIT_TESTING: "1"
        run: |
          pytest --maxfail=1 --disable-warnings -v \
            --cov=backend --cov-report=xml --cov-report=term \
            --junitxml=reports/unit-tests.xml

      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-reports
          path: reports/
          if-no-files-found: warn

  build-and-push:
    needs: tests
    runs-on: ubuntu-latest
    outputs:
      short_sha: ${{ steps.vars.outputs.short_sha }}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set short SHA
        id: vars
        run: echo "short_sha=${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"

      - name: Log in to Azure Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.AZURE_REGISTRY }}
          username: ${{ secrets.AZURE_REGISTRY_USERNAME }}
          password: ${{ secrets.AZURE_REGISTRY_PASSWORD }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push backend image
        uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: true
          tags: ${{ secrets.AZURE_REGISTRY }}/employee-leave-backend:${{ steps.vars.outputs.short_sha }}

      - name: Build and push frontend image
        uses: docker/build-push-action@v6
        with:
          context: ./frontend
          push: true
          tags: ${{ secrets.AZURE_REGISTRY }}/employee-leave-frontend:${{ steps.vars.outputs.short_sha }}

  image-scan:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Create reports directory
        run: mkdir -p reports

      - name: Scan backend image with Trivy
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ${{ secrets.AZURE_REGISTRY }}/employee-leave-backend:${{ needs.build-and-push.outputs.short_sha }}
          format: table
          output: reports/trivy-backend.txt
          severity: HIGH,CRITICAL
          ignore-unfixed: true

      - name: Scan frontend image with Trivy
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ${{ secrets.AZURE_REGISTRY }}/employee-leave-frontend:${{ needs.build-and-push.outputs.short_sha }}
          format: table
          output: reports/trivy-frontend.txt
          severity: HIGH,CRITICAL
          ignore-unfixed: true

      - name: Upload Trivy reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: trivy-reports
          path: reports/
          if-no-files-found: warn

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set short SHA
        run: echo "SHORT_SHA=${{ needs.build-and-push.outputs.short_sha }}" >> "$GITHUB_ENV"

      - name: Set up Helm
        uses: azure/setup-helm@v4

      - name: Set up kubectl
        uses: azure/setup-kubectl@v4
        with:
          version: latest

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBE_CONFIG }}" > ~/.kube/config
          kubectl config current-context
          kubectl get nodes

      - name: Install cert-manager
        run: |
          if ! kubectl get ns cert-manager >/dev/null 2>&1; then
            helm repo add jetstack https://charts.jetstack.io
            helm repo update
            helm upgrade --install cert-manager jetstack/cert-manager \
              --namespace cert-manager \
              --create-namespace \
              --set installCRDs=true \
              --wait --timeout 5m
          fi

      - name: Create ClusterIssuer
        run: |
          cat <<'EOF' | kubectl apply -f -
          apiVersion: cert-manager.io/v1
          kind: ClusterIssuer
          metadata:
            name: letsencrypt-prod
          spec:
            acme:
              email: pascariucosmin93@gmail.com
              server: https://acme-v02.api.letsencrypt.org/directory
              privateKeySecretRef:
                name: letsencrypt-prod
              solvers:
              - http01:
                  ingress:
                    class: nginx
          EOF

      - name: Install NGINX Ingress Controller
        run: |
          if ! kubectl get ns ingress-nginx >/dev/null 2>&1; then
            helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
            helm repo update
            helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
              --namespace ingress-nginx \
              --create-namespace \
              --set controller.service.type=LoadBalancer \
              --set controller.publishService.enabled=true \
              --set controller.service.externalTrafficPolicy=Local \
              --set controller.metrics.enabled=true \
              --set controller.metrics.serviceMonitor.enabled=true \
              --set controller.metrics.serviceMonitor.namespace=monitoring \
              --set controller.metrics.serviceMonitor.additionalLabels.release=prometheus \
              --set controller.autoscaling.enabled=true \
              --set controller.autoscaling.minReplicas=1 \
              --set controller.autoscaling.maxReplicas=5 \
              --set controller.autoscaling.targetCPUUtilizationPercentage=90 \
              --wait --timeout 10m
          fi

      - name: Ensure application namespace exists
        run: kubectl get ns employee-leave >/dev/null 2>&1 || kubectl create ns employee-leave

      - name: Create application secrets
        run: |
          kubectl create secret generic employee-leave-secrets \
            --namespace employee-leave \
            --from-literal=MYSQL_HOST=${{ secrets.MYSQL_HOST }} \
            --from-literal=MYSQL_PORT=${{ secrets.MYSQL_PORT }} \
            --from-literal=MYSQL_USER=${{ secrets.MYSQL_USER }} \
            --from-literal=MYSQL_PASSWORD=${{ secrets.MYSQL_PASSWORD }} \
            --from-literal=MYSQL_DATABASE=${{ secrets.MYSQL_DATABASE }} \
            --from-literal=DISCORD_WEBHOOK=${{ secrets.DISCORD_WEBHOOK }} \
            --dry-run=client -o yaml | kubectl apply -f -

      - name: Create registry pull secret
        run: |
          kubectl create secret docker-registry acr-secret \
            --docker-server=${{ secrets.AZURE_REGISTRY }} \
            --docker-username=${{ secrets.AZURE_REGISTRY_USERNAME }} \
            --docker-password=${{ secrets.AZURE_REGISTRY_PASSWORD }} \
            --docker-email=pascariucosmin93@gmail.com \
            --namespace employee-leave \
            --dry-run=client -o yaml | kubectl apply -f -

      - name: Deploy the application with Helm
        run: |
          helm upgrade --install employee-leave ./employee-leave-management-chart \
            --namespace employee-leave \
            --create-namespace \
            --set backend.image=${{ secrets.AZURE_REGISTRY }}/employee-leave-backend \
            --set backend.tag=${SHORT_SHA} \
            --set frontend.image=${{ secrets.AZURE_REGISTRY }}/employee-leave-frontend \
            --set frontend.tag=${SHORT_SHA} \
            --set ingress.enabled=true \
            --set ingress.className=nginx \
            --set ingress.issuer=letsencrypt-prod \
            --set ingress.tlsSecret=employee-leave-tls \
            --set ingress.host=${{ secrets.DOMAIN_NAME }} \
            --wait --timeout 5m
