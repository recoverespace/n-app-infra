{{- define "chart.service" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ template "chart.fullname" . }}
  labels:
{{ include "chart.labels" . | indent 4 }}
{{- with .Values.service.annotations }}
  annotations:
{{- toYaml . | nindent 4 }}
{{- end }}
spec:
  type: {{ .Values.service.type | default "ClusterIP" }}
{{- if eq "ExternalName" ( .Values.service.type | default "ClusterIP" ) }}
  externalName: {{ tpl .Values.service.externalName . }}
{{- else }}
  ports:
{{- range $port := .Values.service.ports }}
    - port: {{ $port.port }}
      targetPort: {{ $port.targetPort | default $port.port }}
      protocol: {{ $port.protocol | default "TCP" }}
      name: {{ $port.name }}
      {{ if $port.nodePort }}
      nodePort: {{ $port.nodePort }}
      {{ end }}
{{- end }}
  selector:
    app: {{ template "chart.name" . }}
    release: {{ .Release.Name | quote }}
{{- end }}
{{- end }}