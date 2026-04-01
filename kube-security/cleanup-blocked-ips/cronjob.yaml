apiVersion: batch/v1
kind: CronJob
metadata:
  name: ddos-detector-cleanup
  namespace: monitoring
spec:
  schedule: "*/5 * * * *"                # rulează la fiecare 5 minute
  concurrencyPolicy: Forbid              # împiedică suprapunerea joburilor
  successfulJobsHistoryLimit: 2          # păstrează doar ultimele 2 joburi reușite
  failedJobsHistoryLimit: 2              # păstrează doar ultimele 2 joburi eșuate
  startingDeadlineSeconds: 60            # permite întârziere de max 60s la pornire
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          serviceAccountName: calico-admin
          imagePullSecrets:
            - name: regcred
          containers:
            - name: cleanup
              image: cosminregistrydev.azurecr.io/kube-security-clean-ip:1b262e
              imagePullPolicy: IfNotPresent
              env:
                - name: DISCORD_WEBHOOK
                  value: "https://discord.com/api/webhooks/1427216317789765663/JXiAca8FiNTGtRWhv62Me7TDptZKwBUYkmESlKBCC8FdHz0VIH2xg3HSX05JSMBrbfeB"
