# OpenMetrics Auto-Discovery Status

Tracks all `generic-openmetrics-scan` integrations from the autoconfig analysis
(`origin/vitkykra/autoconfig-analysis:analysis/summary_compact.md`).

---

## Discovery support added (e2e tested)

| Integration | Image | Port | Notes |
|---|---|---|---|
| boundary | `hashicorp/boundary` | 9203 | Custom `discover()` override to also derive `health_endpoint` |
| celery | `mher/flower` | 5555 | Switched flower service to vanilla image; auth in broker URL |
| cockroachdb | `cockroachdb/cockroach` | 8080 | Path `/_status/vars`; `discover()` forwarded from V1 wrapper class |
| kong | `kong` | 8001 | `discover()` forwarded from V1 wrapper class |
| krakend | `devopsfaith/krakend` | 8080 | |
| kuma | `kumahq/kuma-cp` | 5680 | |
| n8n | `n8nio/n8n` | 5678 | |
| pulsar | `apachepulsar/pulsar` | 8080 | NaN/Inf regex fix needed in verifier |
| ray | `rayproject/ray` | 8080 | |
| temporal | `temporalio/auto-setup` | 8000 | |

---

## Discovery support not added

### Caddy mock server — ad_identifier cannot match real container

The e2e environment serves fixture files via `caddy:2.7`. The running container's
image is `caddy`, not the integration's real ad_identifier. Discovery fires on the
wrong container in tests and never fires on the right one in production.

| Integration | Real ad_identifier |
|---|---|
| appgate_sdp | `appgate-sdp` |
| aws_neuron | `public.ecr.aws/amazonlinux/amazonlinux` |
| datadog_csi_driver | `gcr.io/datadoghq/csi-driver` |
| dcgm | `nvcr.io/nvidia/cloud-native/dcgm` |
| hugging_face_tgi | `ghcr.io/huggingface/text-generation-inference` |
| karpenter | `public.ecr.aws/karpenter/controller` |
| kubernetes_cluster_autoscaler | `registry.k8s.io/autoscaling/cluster-autoscaler` |
| nvidia_nim | `nvcr.io/nim/*` |
| nvidia_triton | `nvcr.io/nvidia/tritonserver` |
| teleport | `public.ecr.aws/gravitational/teleport` |
| vllm | `vllm/vllm-openai` |

### No canonical image — ad_identifier is arbitrary

There is no single published image that all users run. Any name chosen as
ad_identifier would need to be added to each user's own image, making it
meaningless for zero-config discovery.

| Integration | Notes |
|---|---|
| quarkus | Users build their own Quarkus app images with arbitrary names |

### No Docker e2e environment — no compose setup in tests/

These integrations have no `docker-compose.yaml` in their test directories.
There is no environment in which to run an e2e discovery test.

| Integration | Notes |
|---|---|
| argo_rollouts | |
| argo_workflows | |
| argocd | |
| bentoml | Unit tests only |
| calico | |
| cert_manager | Kubernetes operator |
| cilium | Kubernetes CNI plugin |
| crio | Container runtime, needs host setup |
| datadog_cluster_agent | Requires running agent cluster |
| external_dns | Kubernetes operator |
| fluxcd | |
| keda | Kubernetes operator |
| kube_apiserver_metrics | Kubernetes component |
| kube_controller_manager | Kubernetes component |
| kube_dns | Kubernetes component |
| kube_metrics_server | Kubernetes component |
| kube_proxy | Kubernetes component |
| kubernetes_state | Kubernetes component |
| kubevirt_api | KubeVirt (Kubernetes) |
| kubevirt_controller | KubeVirt (Kubernetes) |
| kubevirt_handler | KubeVirt (Kubernetes) |
| litellm | Unit tests only |
| nginx_ingress_controller | Kubernetes ingress controller |
| strimzi | Kubernetes operator |
| traefik_mesh | Kubernetes service mesh |
| velero | Kubernetes operator |
| weaviate | |

### Docker e2e requires external resources — not standalone

| Integration | Reason |
|---|---|
| azure_iot_edge | Requires Azure IoT Hub credentials (`E2E_IOT_EDGE_CONNSTR`, etc.) |
| linkerd | Docker compose attaches to external `kind` Kubernetes cluster network |

### Uses OpenMetricsBaseCheck V1 — `discover()` not available

These integrations are in the analysis as `generic-openmetrics-scan` candidates
but their check class inherits from `OpenMetricsBaseCheck` (V1), not
`OpenMetricsBaseCheckV2`. The `discover()` classmethod only exists on V2.

| Integration | Notes |
|---|---|
| etcd | `etcd.py` uses `OpenMetricsBaseCheck` |
| gitlab_runner | `gitlab_runner.py` uses `OpenMetricsBaseCheck` |
| scylla | Main exported class uses `OpenMetricsBaseCheck`; V2 class exists but is not exported |

### Base e2e fails to start

| Integration | Failure |
|---|---|
| aerospike | "startup was not complete, exiting immediately" |
| coredns | `HTTPConnectionPool(host='localhost', port=9153): Max retries exceeded` — connection refused |
| falco | `network_mode: host` — `service.ports` is empty; `candidate_ports()` yields nothing |
| milvus | `MilvusException` in script-runner during collection setup (node ID mismatch) |
