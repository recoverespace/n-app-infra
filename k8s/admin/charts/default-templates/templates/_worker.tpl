{{- define "chart.worker" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ template "chart.fullname" . }}-worker
  labels:
{{ include "chart.labels" . | indent 4 }}
spec:
{{- if .Values.workerDeployment }}
  revisionHistoryLimit: {{ .Values.workerDeployment.revisions }}
  replicas: {{ .Values.workerDeployment.replicas }}
  strategy:
    type: {{ .Values.workerDeployment.strategy }}
{{- end }}
  selector:
    matchLabels:
      app: {{ template "chart.name" . }}-worker
      release: {{ .Release.Name | quote }}
  template:
    metadata:
      labels:
        app: {{ template "chart.name" . }}-worker
        release: {{ .Release.Name | quote }}
{{- if .Values.worker.pod }}
{{- with .Values.worker.pod.labels }}
{{ toYaml . | nindent 8 }}
{{- end }}
      annotations:
{{- if .Values.worker.pod.annotations }}
{{- toYaml .Values.worker.pod.annotations | nindent 8 }}
{{- end }}
{{- if .Values.worker.pod.annotationstpl }}
{{- with .Values.worker.pod.annotationstpl }}
{{- tpl . $ | nindent 8 }}
{{- end }}
{{- end }}
{{- end }}
    spec:
{{- if .Values.global.imagePullSecret }}
      imagePullSecrets:
        - name: {{ .Values.global.imagePullSecret }}
{{- else if .Values.image.pullSecret }}
      imagePullSecrets:
        - name: {{ .Values.image.pullSecret }}
{{- end }}
{{- with .Values.worker.initContainers }}
      initContainers:
{{ tpl . $ | nindent 8 }}
{{- end }}
{{- if .Values.worker.pod }}
{{- if .Values.worker.pod.serviceAccount }}
      serviceAccountName: {{ tpl .Values.worker.pod.serviceAccount . }}
{{- end }}
{{- end }}
      containers:
        - name: {{ .Chart.Name }}-worker
          image: "{{ tpl .Values.image.repository . }}/{{ tpl .Values.image.name . }}:{{ tpl .Values.image.tag . }}"
{{- with .Values.worker.command }}
          command: 
{{ toYaml . | nindent 12  }}
{{- end }}
{{- with .Values.worker.args }}
          args: 
{{ toYaml . | nindent 12  }}
{{- end }}
{{- with .Values.worker.securityContext }}
          securityContext:
{{ toYaml . | nindent 12 }}
{{- end }}
{{- if .Values.worker.image.pullPolicy }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
{{- end }}
{{ if .Values.worker.service }}
          ports:
{{- range $port := .Values.worker.service.ports }}
            - containerPort: {{ $port.targetPort | default $port.port }}
              name: {{ $port.name }}
{{- end }}
{{- end }}
{{- with .Values.worker.livenessProbe }}
          livenessProbe:
{{- toYaml . | nindent 12 }}
{{- end }}
{{- with .Values.worker.readinessProbe }}
          readinessProbe:
{{- toYaml . | nindent 12 }}
{{- end }}
{{- with .Values.worker.startupProbe }}
          startupProbe:
{{- toYaml . | nindent 12 }}
{{- end }}
          env:
{{- with .Values.worker.extraEnv }}
{{- toYaml . | nindent 12 }}
{{- end }}
{{- range $envVarGroup := .Values.worker.envVarGroups }}
    {{- range $key, $value := ( index $.Values.global.envVarGroups $envVarGroup ) }}
        {{- printf "- name: %s\n  value: %s" $key ($value | toString | quote) | nindent 12 }}
    {{- end }}
{{- end }}
{{- range $key, $value := .Values.worker.envVars }}
    {{- printf "- name: %s\n  value: %s" $key ($value | toString | quote) | nindent 12 }}
{{- end }}
{{- with .Values.worker.envFrom }}
          envFrom:
{{- tpl . $ | nindent 12 }}
{{- end }}
{{- with .Values.worker.volumeMounts }}
          volumeMounts:
{{ toYaml . | nindent 12 }}
{{- end }}
{{- with .Values.worker.resources }}
          resources:
{{ toYaml . | nindent 12 }}
{{- end }}
{{- with .Values.worker.extraContainers }}
{{ tpl . $ | nindent 8 }}
{{- end }}
{{- with .Values.worker.nodeSelector }}
      nodeSelector:
{{ toYaml . | nindent 8 }}
{{- end }}
{{- with .Values.worker.affinity }}
      affinity:
{{ toYaml . | nindent 8 }}
{{- end }}
{{- with .Values.worker.tolerations }}
      tolerations:
{{ toYaml . | nindent 8 }}
{{- end }}
      volumes:
{{- with .Values.worker.volumes }}
{{- toYaml . | nindent 8 }}
{{- end }}
{{- end }}