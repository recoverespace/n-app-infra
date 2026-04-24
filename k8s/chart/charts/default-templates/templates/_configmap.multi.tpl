{{- define "chart.configmap.multi" -}}
{{- range $configmap, $val := .Values.configmaps }}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ $configmap }}
  labels:
  annotations:
    "helm.sh/hook": pre-upgrade
{{ include "chart.labels" $ | indent 4 }}
data:
{{- with .values }}
{{- toYaml . | nindent 2 }}
{{- end }}
---
{{- end }}
{{- end }}