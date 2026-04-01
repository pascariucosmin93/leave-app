apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-frontend
  namespace: {{ .Values.namespace }}
spec:
  {{- if not .Values.frontend.autoscaling.enabled }}
  replicas: {{ default 2 .Values.frontend.replicaCount }}
  {{- end }}
  strategy:
    {{- toYaml .Values.frontend.strategy | nindent 4 }}
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: frontend
          image: "{{ .Values.frontend.image }}:{{ .Values.frontend.tag }}"
          ports:
            - containerPort: {{ .Values.frontend.port }}
          resources:
            {{- toYaml .Values.frontend.resources | nindent 12 }}
          livenessProbe:
            httpGet:
              path: /
              port: {{ .Values.frontend.port }}
            initialDelaySeconds: 10
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /
              port: {{ .Values.frontend.port }}
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
