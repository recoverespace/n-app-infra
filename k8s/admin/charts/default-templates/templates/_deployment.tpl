{{- define "chart.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ template "chart.fullname" . }}
  labels:
{{ include "chart.labels" . | indent 4 }}
spec:
{{- if .Values.deployment }}
  revisionHistoryLimit: {{ .Values.deployment.revisions }}
  replicas: {{ .Values.deployment.replicas }}
  strategy:
    type: {{ .Values.deployment.strategy }}
{{- end }}
  selector:
    matchLabels:
      app: {{ template "chart.name" . }}
      release: {{ .Release.Name | quote }}
  template:
    metadata:
      labels:
        app: {{ template "chart.name" . }}
        release: {{ .Release.Name | quote }}
{{- if .Values.pod }}
{{- with .Values.pod.labels }}
{{ toYaml . | nindent 8 }}
{{- end }}
      annotations:
{{- if .Values.pod.annotations }}
{{- toYaml .Values.pod.annotations | nindent 8 }}
{{- end }}
{{- if .Values.pod.annotationstpl }}
{{- with .Values.pod.annotationstpl }}
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
{{- with .Values.initContainers }}
      initContainers:
{{ tpl . $ | nindent 8 }}
{{- end }}
{{- if .Values.pod }}
{{- if .Values.pod.serviceAccount }}
      serviceAccountName: {{ tpl .Values.pod.serviceAccount . }}
{{- end }}
{{- end }}
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ tpl .Values.image.repository . }}/{{ tpl .Values.image.name . }}:{{ tpl .Values.image.tag . }}"
{{- with .Values.command }}
          command: 
{{ toYaml . | nindent 12  }}
{{- end }}
{{- with .Values.args }}
          args: 
{{ toYaml . | nindent 12  }}
{{- end }}
{{- with .Values.securityContext }}
          securityContext:
{{ toYaml . | nindent 12 }}
{{- end }}
{{- if .Values.image.pullPolicy }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
{{- end }}
{{ if .Values.service }}
          ports:
{{- range $port := .Values.service.ports }}
            - containerPort: {{ $port.targetPort | default $port.port }}
              name: {{ $port.name }}
{{- end }}
{{- end }}
{{- with .Values.livenessProbe }}
          livenessProbe:
{{- toYaml . | nindent 12 }}
{{- end }}
{{- with .Values.readinessProbe }}
          readinessProbe:
{{- toYaml . | nindent 12 }}
{{- end }}
{{- with .Values.startupProbe }}
          startupProbe:
{{- toYaml . | nindent 12 }}
{{- end }}
          env:
{{- with .Values.extraEnv }}
{{- toYaml . | nindent 12 }}
{{- end }}
{{- range $envVarGroup := .Values.envVarGroups }}
    {{- range $key, $value := ( index $.Values.global.envVarGroups $envVarGroup ) }}
        {{- printf "- name: %s\n  value: %s" $key ($value | toString | quote) | nindent 12 }}
    {{- end }}
{{- end }}
{{- range $key, $value := .Values.envVars }}
    {{- printf "- name: %s\n  value: %s" $key ($value | toString | quote) | nindent 12 }}
{{- end }}
{{- with .Values.envFrom }}
          envFrom:
{{- tpl . $ | nindent 12 }}
{{- end }}
{{- with .Values.volumeMounts }}
          volumeMounts:
{{ toYaml . | nindent 12 }}
{{- end }}
{{- with .Values.resources }}
          resources:
{{ toYaml . | nindent 12 }}
{{- end }}
{{- with .Values.extraContainers }}
{{ tpl . $ | nindent 8 }}
{{- end }}
{{- with .Values.nodeSelector }}
      nodeSelector:
{{ toYaml . | nindent 8 }}
{{- end }}
{{- with .Values.affinity }}
      affinity:
{{ toYaml . | nindent 8 }}
{{- end }}
{{- with .Values.tolerations }}
      tolerations:
{{ toYaml . | nindent 8 }}
{{- end }}
      volumes:
{{- with .Values.volumes }}
{{- toYaml . | nindent 8 }}
{{- end }}
{{- end }}