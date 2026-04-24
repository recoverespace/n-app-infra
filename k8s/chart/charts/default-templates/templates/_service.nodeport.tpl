{{- define "chart.service.nodeport" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ template "chart.fullname" . }}-nodeport
  labels:
{{ include "chart.labels" . | indent 4 }}
spec:
  type: NodePort
  ports:
    {{- range $port := .Values.service.ports }}
    - port: {{ $port.port }}
      targetPort: {{ $port.targetPort | default $port.port }}
      protocol: {{ $port.protocol | default "TCP" }}
      {{ if $port.nodePort }}
      nodePort: {{ $port.nodePort }}
      {{ end }}
    {{- end }}
  selector:
    app: {{ template "chart.name" . }}
    release: {{ .Release.Name | quote }}
{{- end }}