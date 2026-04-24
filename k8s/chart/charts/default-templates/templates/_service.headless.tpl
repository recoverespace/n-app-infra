{{- define "chart.service.headless" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ .Values.statefulset.serviceName }}
  labels:
{{ include "chart.labels" . | indent 4 }}
spec:
  type: ClusterIP
  clusterIP: None
  ports:
{{- range $port := .Values.service.ports }}
    - port: {{ $port.port }}
      targetPort: {{ $port.targetPort | default $port.port }}
      protocol: {{ $port.protocol | default "TCP" }}
      name: {{ $port.name }}
{{- end }}
  selector:
    app: {{ template "chart.name" . }}
    release: {{ .Release.Name | quote }}
{{- end }}