{{/*
   This version of the validatingwebhookconfiguration is applied indirectly
   by galley. This exists to support a smoother upgrade path from istio
   Rversions < 1.4
*/}}
{{ define "validatingwebhookconfiguration.yaml.tpl" }}
apiVersion: admissionregistration.k8s.io/v1beta1
kind: ValidatingWebhookConfiguration
metadata:
  name: istio-galley
  labels:
    app: {{ template "galley.name" . }}
    chart: {{ template "galley.chart" . }}
    heritage: {{ .Release.Service }}
    release: {{ .Release.Name }}
    istio: galley
webhooks:
  - name: pilot.validation.istio.io
    clientConfig:
      service:
        name: istio-galley
        namespace: {{ .Release.Namespace }}
        path: "/admitpilot"
      caBundle: ""
    rules:
      - operations:
        - CREATE
        - UPDATE
        apiGroups:
        - config.istio.io
        apiVersions:
        - v1alpha2
        resources:
        - httpapispecs
        - httpapispecbindings
        - quotaspecs
        - quotaspecbindings
      - operations:
        - CREATE
        - UPDATE
        apiGroups:
        - rbac.istio.io
        apiVersions:
        - "*"
        resources:
        - "*"
      - operations:
        - CREATE
        - UPDATE
        apiGroups:
        - security.istio.io
        apiVersions:
        - "*"
        resources:
        - "*"
      - operations:
        - CREATE
        - UPDATE
        apiGroups:
        - authentication.istio.io
        apiVersions:
        - "*"
        resources:
        - "*"
      - operations:
        - CREATE
        - UPDATE
        apiGroups:
        - networking.istio.io
        apiVersions:
        - "*"
        resources:
        - destinationrules
        - envoyfilters
        - gateways
        - serviceentries
        - sidecars
        - virtualservices
    # Fail open until the validation webhook is ready. The webhook controller
    # will update this to `Fail` and patch in the `caBundle` when the webhook
    # endpoint is ready.
    failurePolicy: Ignore
    sideEffects: None
  - name: mixer.validation.istio.io
    clientConfig:
      service:
        name: istio-galley
        namespace: {{ .Release.Namespace }}
        path: "/admitmixer"
      caBundle: ""
    rules:
      - operations:
        - CREATE
        - UPDATE
        apiGroups:
        - config.istio.io
        apiVersions:
        - v1alpha2
        resources:
        - rules
        - attributemanifests
        - adapters
        - handlers
        - instances
        - templates
    # Fail open until the validation webhook is ready. The webhook controller
    # will update this to `Fail` and patch in the `caBundle` when the webhook
    # endpoint is ready.
    failurePolicy: Ignore
    sideEffects: None
{{- end }}
