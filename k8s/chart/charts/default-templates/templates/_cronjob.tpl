{{- define "chart.cronjob" -}}
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: {{ if .Values.cronjob.name}}{{ .Values.cronjob.name }}{{ else }}{{ template "chart.fullname" . }}{{ end }}
  labels:
{{ include "chart.labels" . | indent 4 }}
{{- with .Values.cronjob.annotations }}
  annotations:
{{- toYaml . | nindent 4 }}
{{- end }}
spec:
  concurrencyPolicy: {{ .Values.cronjob.concurrencyPolicy | toString }}
  failedJobsHistoryLimit: {{ .Values.cronjob.failedHistory }}
  successfulJobsHistoryLimit: {{ .Values.cronjob.successHistory }}
  schedule: {{ .Values.cronjob.schedule }}
  jobTemplate:
    spec:
      template:
        spec:
{{- if .Values.global.imagePullSecret }}
          imagePullSecrets:
            - name: {{ .Values.global.imagePullSecret }}
{{- else if .Values.cronjob.image.pullSecret }}
          imagePullSecrets:
            - name: {{ .Values.cronjob.image.pullSecret }}
{{ end }}
          containers:
          - name: {{ .Chart.Name }}-cronjob
            image: "{{ tpl .Values.cronjob.image.repository . }}/{{ tpl .Values.cronjob.image.name . }}:{{ tpl .Values.cronjob.image.tag . }}"
            imagePullPolicy: {{ .Values.cronjob.image.pullPolicy }}
{{- with .Values.cronjob.command }}
            command: 
{{ toYaml . | nindent 14  }}
{{- end }}
{{- with .Values.cronjob.args }}
            args: 
{{ toYaml . | nindent 14  }}
{{- end }}
            env:
{{ toYaml .Values.cronjob.extraEnv | nindent 14 }}
{{- range $envVarGroup := .Values.cronjob.envVarGroups }}
    {{- range $key, $value := ( index $.Values.global.envVarGroups $envVarGroup ) }}
        {{- printf "- name: %s\n  value: %s" $key ($value | toString | quote) | nindent 14 }}
    {{- end }}
{{- end }}
{{- range $key, $value := .Values.cronjob.envVars }}
    {{- printf "- name: %s\n  value: %s" $key ($value | toString | quote) | nindent 14 }}
{{- end }}
{{- with .Values.cronjob.envFrom }}
            envFrom:
{{ tpl . $ | nindent 14 }}
{{- end }}
{{- with .Values.cronjob.volumeMounts }}
            volumeMounts:
{{- toYaml . | nindent 14 }}
{{- end }}
{{- with .Values.cronjob.volumes }}
          volumes:
{{- toYaml . | nindent 12 }}
{{- end }}
          restartPolicy: {{ .Values.cronjob.restartPolicy | quote }}
{{- with .Values.cronjob.nodeSelector }}
          nodeSelector:
{{- toYaml . | nindent 12 }}
{{- end }}
{{- end }}