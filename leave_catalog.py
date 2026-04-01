name: Deploy Monitoring Stack

on:
  workflow_dispatch:
  workflow_run:
    workflows: ["Build, Push, Scan and Deploy"]
    types:
      - completed

jobs:
  deploy-monitoring:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

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

      - name: Ensure monitoring namespace exists
        run: kubectl get ns monitoring >/dev/null 2>&1 || kubectl create ns monitoring

      - name: Install or upgrade Prometheus
        run: |
          helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
          helm repo update

          kubectl create secret generic additional-scrape-configs \
            --from-file=additional-scrape-configs.yaml=docs/monitoring/additional-scrape-configs.yaml \
            -n monitoring --dry-run=client -o yaml | kubectl apply -f -

          helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
            --namespace monitoring --create-namespace \
            --set grafana.enabled=false \
            --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
            --set prometheus.prometheusSpec.serviceMonitorSelector.matchLabels.release=prometheus \
            --set prometheus.service.type=ClusterIP \
            --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.accessModes[0]=ReadWriteOnce \
            --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=20Gi \
            --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=managed-csi \
            --set prometheus.prometheusSpec.retention=15d \
            --set prometheus.prometheusSpec.additionalScrapeConfigs.name=additional-scrape-configs \
            --set prometheus.prometheusSpec.additionalScrapeConfigs.key=additional-scrape-configs.yaml \
            --wait --timeout 10m

      - name: Patch Prometheus additional scrape configs
        run: |
          kubectl patch prometheus prometheus-kube-prometheus-prometheus -n monitoring \
            --type merge \
            -p '{"spec":{"additionalScrapeConfigs":{"name":"additional-scrape-configs","key":"additional-scrape-configs.yaml"}}}'

      - name: Deploy backend ServiceMonitor
        run: |
          cat <<'EOF' | kubectl apply -f -
          apiVersion: monitoring.coreos.com/v1
          kind: ServiceMonitor
          metadata:
            name: employee-leave-backend-monitor
            namespace: monitoring
            labels:
              release: prometheus
          spec:
            selector:
              matchLabels:
                app: backend
            namespaceSelector:
              matchNames:
                - employee-leave
            endpoints:
              - port: http
                path: /metrics
                interval: 15s
                scrapeTimeout: 5s
          EOF

      - name: Install Loki
        run: |
          helm repo add grafana https://grafana.github.io/helm-charts
          helm repo update
          helm upgrade --install loki grafana/loki-stack \
            --namespace monitoring \
            --set grafana.enabled=false \
            --set prometheus.enabled=false \
            --wait --timeout 5m

      - name: Install Grafana
        run: |
          helm upgrade --install grafana grafana/grafana \
            --namespace monitoring \
            --set persistence.enabled=true \
            --set persistence.size=10Gi \
            --set persistence.storageClassName=managed-csi \
            --set adminUser=admin \
            --set adminPassword=${{ secrets.GRAFANA_ADMIN_PASSWORD }} \
            --set service.type=ClusterIP \
            --set ingress.enabled=true \
            --set ingress.ingressClassName=nginx \
            --set-string ingress.annotations."cert-manager\.io/cluster-issuer"="letsencrypt-prod" \
            --set ingress.hosts[0]="${{ secrets.DOMAIN_NAME }}" \
            --set ingress.tls[0].hosts[0]="${{ secrets.DOMAIN_NAME }}" \
            --set ingress.tls[0].secretName="grafana-tls" \
            --set datasources."datasources\.yaml".apiVersion=1 \
            --set datasources."datasources\.yaml".datasources[0].name="Prometheus" \
            --set datasources."datasources\.yaml".datasources[0].type="prometheus" \
            --set datasources."datasources\.yaml".datasources[0].url="http://prometheus-operated.monitoring.svc:9090" \
            --set datasources."datasources\.yaml".datasources[0].access="proxy" \
            --set datasources."datasources\.yaml".datasources[0].isDefault=true \
            --set datasources."datasources\.yaml".datasources[1].name="Loki" \
            --set datasources."datasources\.yaml".datasources[1].type="loki" \
            --set datasources."datasources\.yaml".datasources[1].url="http://loki.monitoring.svc:3100" \
            --set datasources."datasources\.yaml".datasources[1].access="proxy" \
            --wait --timeout 10m

      - name: Install Blackbox Exporter
        run: |
          helm upgrade --install blackbox-exporter prometheus-community/prometheus-blackbox-exporter \
            --namespace monitoring \
            --set serviceMonitor.enabled=true \
            --set serviceMonitor.additionalLabels.release=prometheus \
            --set ingress.enabled=true \
            --set ingress.ingressClassName=nginx \
            --set ingress.hosts[0].host="blackbox.${{ secrets.DOMAIN_NAME }}" \
            --set ingress.hosts[0].paths[0].path="/" \
            --set ingress.hosts[0].paths[0].pathType=Prefix \
            --set ingress.tls[0].hosts[0]="blackbox.${{ secrets.DOMAIN_NAME }}" \
            --set ingress.tls[0].secretName="blackbox-tls" \
            --wait --timeout 5m
