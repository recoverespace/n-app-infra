{{- define "chart.secret.multi" -}}
{{- range $secret, $val := .Values.secrets }}
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: {{ $secret }}
  labels:
{{ include "chart.labels" $ | indent 4 }}
data:
{{- range $key, $value := .values }}
{{- printf "%s: %s" $key ($value | toString | b64enc | quote) | nindent 2 }}
{{- end }}
{{- with .tplvalues }}
{{ tpl . $ | nindent 2 }}
{{- end }}
---
{{- end }}
{{- end }}