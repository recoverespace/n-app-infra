{{- define "chart.secret.external.aws.multi" -}}
{{- range $secret, $val := .Values.extSecrets }}
apiVersion: kubernetes-client.io/v1
kind: ExternalSecret
  name: {{ $secret }}
  labels:
{{ include "chart.labels" $ | indent 4 }}
spec:
  backendType: systemManager
  data:
{{- range $name, $key := .values }}
{{- printf "- name: %s\n  key: %s" $name ($key | toString ) | nindent 4 }}
{{- end }}
---
{{- end }}
{{- end }}