{{- define "chart.hpa" -}}
apiVersion: autoscaling/v2beta2
kind: HorizontalPodAutoscaler 
metadata:
  name: {{ template "chart.fullname" . }}
  labels:
{{ include "chart.labels" . | indent 4 }}
spec: 
  maxReplicas: {{ .Values.hpa.maxReplicas }}
  minReplicas: {{ .Values.hpa.minReplicas }}
  scaleTargetRef: 
    apiVersion: apps/v1 
    kind: Deployment 
    name: {{ template "chart.fullname" . }} 
  metrics: 
{{- with .Values.hpa.metrics }}
{{- toYaml . | nindent 4 }}
{{- end }}
{{- end }}
