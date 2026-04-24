{{- define "chart.ingress.multi" }}
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
{{ if .Values.ingress.tls.enabled | default ("true") }}
  tls:
    - hosts:
      {{- range $ingress, $val := .Values.ingress.config }}
      {{- printf "- %s" ($ingress | toString | quote) | nindent 8 }}
      {{- end }}
      {{- range $domain := .Values.ingress.extraDomains }}
      {{- printf "- %s" ($domain | toString | quote) | nindent 8 }}
      {{- end }}
      {{ if .Values.ingress.tls.secretName }}
      secretName: {{ .Values.ingress.tls.secretName }}
      {{ else }}
      secretName: {{ template "chart.fullname" . }}-tls
      {{ end }}
{{ end }}  
  rules:
{{- range $domain, $val := .Values.ingress.config }}
    - host: {{ $domain }}
      http:
        paths:
        - path: {{ .path | default ("/") }}
          pathType: {{ .pathType | default ("ImplementationSpecific") }}
          backend:
            service:
              name: {{ include "chart.fullname" $ }}
              port:
                number: {{ .port | default ((index $.Values.service.ports 0).port)}}
{{- end }}
{{- end }}
