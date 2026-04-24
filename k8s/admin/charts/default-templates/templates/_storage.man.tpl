{{- define "chart.storage.manual" -}}
apiVersion: v1
kind: PersistentVolume
metadata:
  name: {{ .Values.persistence.claimName | quote }}
  labels:
{{ include "chart.labels" . | indent 4 }}
spec:
  storageClassName: {{ .Values.persistence.storageClass | quote }}
  capacity:
    storage: {{ .Values.persistence.size | quote }}
  accessModes:
    - {{ .Values.persistence.accessMode | quote }}
  hostPath:
    path: {{ .Values.persistence.hostPath | quote }}
---
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: {{ .Values.persistence.claimName | quote }}
  labels:
{{ include "chart.labels" . | indent 4 }}
spec:
  accessModes:
    - {{ .Values.persistence.accessMode | quote }}
  resources:
    requests:
      storage: {{ .Values.persistence.size | quote }}
  storageClassName: {{ .Values.persistence.storageClass | quote }}
{{- end }}
