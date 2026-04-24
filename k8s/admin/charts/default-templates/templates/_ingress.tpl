{{- define "chart.ingress" }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ template "chart.fullname" . }}
  labels:
{{ include "chart.labels" . | indent 4 }}
{{- with .Values.ingress.annotations }}
  annotations:
{{- toYaml . | nindent 4 }}
{{- end }}
spec:
{{ if .Values.ingress.tls.enabled }}
  tls:
    - hosts:
      {{ if .Values.ingress.tls.hosts }}
      {{- range $host := .Values.ingress.tls.hosts }}
        {{- printf "- %s" ($host | toString | quote) | nindent 8 }}
      {{- end }}
      {{ else }}
        - {{ tpl .Values.ingress.domain . }}
      {{ end }}
      {{ if .Values.ingress.tls.secretName }}
      secretName: {{ .Values.ingress.tls.secretName }}
      {{ else }}
      secretName: {{ tpl .Values.ingress.domain . }}-tls
      {{ end }}
{{ end }}      
  rules:
    - host: {{ tpl .Values.ingress.domain . }}
      http:
        paths:
        - path: {{ .Values.ingress.path | default ("/") }}
          pathType: {{ .Values.ingress.pathType | default ("ImplementationSpecific") }}
          backend:
            service:
              name: {{ template "chart.fullname" . }}
              port:
                number: {{ (index .Values.service.ports 0).port }}
{{- end }}
