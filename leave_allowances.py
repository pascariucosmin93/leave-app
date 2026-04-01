name: Apply Kube Security

on:
  workflow_dispatch:
  workflow_run:
    workflows: ["Build, Push, Scan and Deploy"]
    types:
      - completed

jobs:
  apply-kube-security:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

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

      - name: Log in to Azure Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.AZURE_REGISTRY }}
          username: ${{ secrets.AZURE_REGISTRY_USERNAME }}
          password: ${{ secrets.AZURE_REGISTRY_PASSWORD }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Set short SHA
        id: vars
        run: echo "short_sha=${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"

      - name: Build and push DDoS detector image
        uses: docker/build-push-action@v6
        with:
          context: ./kube-security/ddos
          push: true
          tags: ${{ secrets.AZURE_REGISTRY }}/kube-security-ddos:${{ steps.vars.outputs.short_sha }}

      - name: Build and push cleanup image
        uses: docker/build-push-action@v6
        with:
          context: ./kube-security/clean-ip
          push: true
          tags: ${{ secrets.AZURE_REGISTRY }}/kube-security-clean-ip:${{ steps.vars.outputs.short_sha }}

      - name: Patch images in manifests
        run: |
          DDOS_IMG="${{ secrets.AZURE_REGISTRY }}/kube-security-ddos:${{ steps.vars.outputs.short_sha }}"
          CLEAN_IMG="${{ secrets.AZURE_REGISTRY }}/kube-security-clean-ip:${{ steps.vars.outputs.short_sha }}"
          sed -i "s|image: .*kube-security-ddos[:@][^\"']*|image: ${DDOS_IMG}|" kube-security/ddos/ddos-detector-loki-cronjob.yaml || true
          sed -i "s|image: .*kube-security-clean-ip[:@][^\"']*|image: ${CLEAN_IMG}|" kube-security/clean-ip/ddos-cleanup-cronjob.yaml || true

      - name: Apply DDoS detector cronjob
        run: kubectl apply -n monitoring -f kube-security/ddos/ddos-detector-loki-cronjob.yaml

      - name: Apply blocked IP cleanup cronjob
        run: kubectl apply -n monitoring -f kube-security/clean-ip/ddos-cleanup-cronjob.yaml

      - name: Apply pod network policies
        run: |
          if [ -d "kube-security/pods-network" ]; then
            for f in kube-security/pods-network/*.yaml; do
              [ -e "$f" ] || continue
              kubectl apply -f "$f"
            done
          fi

      - name: Apply Calico admin ServiceAccount and RBAC
        run: |
          if [ -f "kube-security/calico-admin-sa.yaml" ]; then
            kubectl apply -f kube-security/calico-admin-sa.yaml
          fi
