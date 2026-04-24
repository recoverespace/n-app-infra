{{- define "chart.statefulset" -}}
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ template "chart.fullname" . }}
  labels:
{{ include "chart.labels" . | indent 4 }}
{{- with .Values.statefulset.annotations }}
  annotations:
{{ toYaml . | nindent 4 }}
{{- end }}
spec:
{{ if .Values.persistence }}
  volumeClaimTemplates:
{{- range $pers := .Values.persistence }}
  - metadata:
      name: {{ $pers.name }}
    spec:
      accessModes: 
        {{ $pers.accessModes | default ("ReadWriteOnce") | quote }}
      storageClassName: {{ $pers.storageClassName | quote }}
      resources:
        requests:
          storage: {{ $pers.size | quote }}
{{- end }}
{{- end }}
  podManagementPolicy: {{ .Values.statefulset.podManagementPolicy | default ("OrderedReady") }}
  revisionHistoryLimit: {{ .Values.statefulset.revisions | default ("3") }}
  replicas: {{ .Values.statefulset.replicas | default ("1") }}
  serviceName: {{ template "chart.fullname" . }}-headless
  updateStrategy:
    type: {{ .Values.statefulset.updateStrategy | default ("RollingUpdate") }}
  selector:
    matchLabels:
      app: {{ template "chart.name" . }}
      release: {{ .Release.Name | quote }}
  template:
    metadata:
      labels:
        app: {{ template "chart.name" . }}
        release: {{ .Release.Name | quote }}
{{- if .Values.pod.labels }}
{{- toYaml .Values.pod.labels | nindent 8 }}
{{- end }}
{{- if .Values.pod.annotations }}
      annotations:
{{ toYaml .Values.pod.annotations | nindent 8 }}
{{- end }}
    spec:
{{- if .Values.global.imagePullSecret }}
      imagePullSecrets:
        - name: {{ .Values.global.imagePullSecret }}
{{- else }}
      imagePullSecrets:
        - name: {{ .Values.image.pullSecret }}
{{- end }}
{{- if .Values.initContainers }}
      initContainers:
{{- with .Values.initContainers }}
{{- tpl . $ | nindent 8 }}
{{- end }}
{{- end }}
{{- if .Values.pod.serviceAccount }}
      serviceAccountName: {{ .Values.pod.serviceAccount }}
{{- end }}
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ tpl .Values.image.repository . }}/{{ tpl .Values.image.name . }}:{{ tpl .Values.image.tag . }}"
{{- if .Values.command }}
          command: 
{{ toYaml .Values.command | nindent 12  }}
{{- end }}
{{- if .Values.args }}
          args: 
{{ toYaml .Values.args | nindent 12  }}
{{- end }}
{{- if .Values.securityContext }}
          securityContext:
{{- toYaml .Values.securityContext | nindent 12 }}
{{- end }}
{{- if .Values.image.pullPolicy }}
          imagePullPolicy: {{ .Values.image.pullPolicy }}
{{- end }}
          ports:
{{ if .Values.pod.ports }}
{{- range $port := .Values.pod.ports }}
            - containerPort: {{ $port.port }}
              name: {{ $port.name }}
{{- end }}
{{- else }}
{{- range $port := .Values.service.ports }}
            - containerPort: {{ $port.targetPort | default $port.port }}
              name: {{ $port.name }}
{{- end }}
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
{{- with .Values.volumeMounts }}
          volumeMounts:
{{- toYaml . | nindent 10 }}
{{- end }}
{{- with .Values.resources }}
          resources:
{{ toYaml . | indent 12 }}
{{- end }}
{{- with .Values.extraContainers }}
{{- tpl . $ | nindent 8 }}
{{- end }}
{{- with .Values.nodeSelector }}
      nodeSelector:
{{ toYaml . | indent 8 }}
{{- end }}
{{- with .Values.affinity }}
      affinity:
{{ toYaml . | indent 8 }}
{{- end }}
{{- with .Values.tolerations }}
      tolerations:
{{ toYaml . | indent 8 }}
{{- end }}
{{- with .Values.volumes }}
      volumes:
{{- toYaml . | nindent 8 }}
{{- end }}
{{- end }}
---
apiVersion: v1
kind: Service
metadata:
  name: {{ template "chart.fullname" . }}-headless
  labels:
    app: {{ template "chart.name" . }}
    chart: {{ template "chart.chart" . }}
    release: {{ .Release.Name | quote }}
    heritage: {{ .Release.Service | quote }}
spec:
  type: ClusterIP
  clusterIP: None
  ports:
{{- range $port := .Values.service.ports }}
    - port: {{ $port.port }}
      targetPort: {{ $port.targetPort | default $port.port }}
      protocol: {{ $port.protocol | default "TCP" }}
      name: {{ $port.name }}
{{- end }}
  selector:
    app: {{ template "chart.name" . }}
    release: {{ .Release.Name | quote }}
