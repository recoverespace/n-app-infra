{{- define "chart.configmap" -}}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ if .Values.configmap.name }}{{ .Values.configmap.name }}{{else}}{{ template "chart.fullname" . }}{{ end }}
  labels:
{{ include "chart.labels" . | indent 4 }}
data:
{{- range $key, $value := .Values.configmap.values }}
{{- printf "%s: %s" $key ($value | toString | quote) | nindent 2 }}
{{- end }}
{{- with .Values.configmap.tplvalues }}
{{ tpl . $ | nindent 2 }}
{{- end }}
{{- end }}