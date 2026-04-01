apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-restrict-basic
  namespace: employee-leave
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # 🔹 Permite trafic DOAR de la Ingress-NGINX (utilizatorii externi)
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 80

  egress:
    # 🔹 Permite DNS (către CoreDNS în kube-system)
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53

    # Allow communication to the backend inside the employee-leave namespace.
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: employee-leave
          podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 5000
