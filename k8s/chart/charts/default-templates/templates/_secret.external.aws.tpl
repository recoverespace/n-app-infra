{{- define "chart.secret.external.aws" -}}
apiVersion: kubernetes-client.io/v1
kind: ExternalSecret
metadata:
  name: {{ if .Values.extSecret.name }}{{ .Values.extSecret.name }}{{else}}{{ template "chart.fullname" . }}{{ end }}
  labels:
{{ include "chart.labels" . | indent 4 }}
spec:
  backendType: systemManager
  data:
{{- range $name, $key := .Values.extSecret.values }}
{{- printf "- name: %s\n  key: %s" $name ($key | toString ) | nindent 4 }}
{{- end }}
{{- end }}