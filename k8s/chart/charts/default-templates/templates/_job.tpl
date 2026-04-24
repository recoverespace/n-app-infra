{{- define "chart.job" -}}
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ if .Values.job.name}}{{ .Values.job.name }}{{ else }}{{ template "chart.fullname" . }}{{ end }}
  labels:
{{ include "chart.labels" . | indent 4 }}
{{- with .Values.job.annotations }}
  annotations:
{{- toYaml . | nindent 4 }}
{{- end }}
spec:
  concurrencyPolicy: {{ .Values.job.concurrencyPolicy | quote }}
  ttlSecondsAfterFinished: {{ .Values.job.ttlSecondsAfterFinished }}
  template:
    metadata:
      name: {{ .Values.job.name }}
    spec:
{{- if .Values.global.imagePullSecret }}
      imagePullSecrets:
        - name: {{ .Values.global.imagePullSecret }}
{{- else if .Values.job.image.pullSecret }}
      imagePullSecrets:
        - name: {{ .Values.job.image.pullSecret }}
{{ end }}
      containers:
      - name: {{ .Chart.Name }}-job
        image: "{{ tpl .Values.image.repository . }}/{{ tpl .Values.image.name . }}:{{ tpl .Values.image.tag . }}"
        imagePullPolicy: {{ .Values.job.image.pullPolicy }}
{{- with .Values.job.command }}
        command: 
{{ toYaml . | nindent 10  }}
{{- end }}
{{- with .Values.job.args }}
        args: 
{{ toYaml . | nindent 10  }}
{{- end }}
        env:
{{- range $envVarGroup := .Values.job.envVarGroups }}
    {{- range $key, $value := ( index $.Values.global.envVarGroups $envVarGroup ) }}
        {{- printf "- name: %s\n  value: %s" $key ($value | toString | quote) | nindent 10 }}
    {{- end }}
{{- end }}
{{- if .Values.job.envVars }}
    {{- range $key, $value := .Values.job.envVars }}
        {{- printf "- name: %s\n  value: %s" $key ($value | toString | quote) | nindent 10 }}
    {{- end }}
{{- end }}
{{- if .Values.job.extraEnv }}
    {{ toYaml .Values.job.extraEnv | nindent 10 }}
{{- end }}
{{- if .Values.global.extraEnv }}
    {{ toYaml .Values.global.extraEnv | nindent 10 }}
{{- end }}
{{- if .Values.job.envFrom }}
        envFrom:
    {{ tpl .Values.job.envFrom . | nindent 10 }}
{{- end }}
{{- with .Values.job.volumeMounts }}
        volumeMounts:
{{- toYaml . | nindent 10 }}
{{- end }}
{{- with .Values.resources }}
        resources:
{{ toYaml . | nindent 10 }}
{{- end }}
      volumes:
{{- with .Values.job.volumes }}
{{- toYaml . | nindent 8 }}
{{- end }}
{{- with .Values.job.volumesTpl }}
{{- tpl . $ | nindent 8 }}
{{- end }}
      restartPolicy: {{ .Values.job.restartPolicy | quote }}
{{- with .Values.job.nodeSelector }}
      nodeSelector:
{{- toYaml . | nindent 8 }}
{{- end }}
{{- end }}