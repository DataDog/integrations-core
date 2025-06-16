#!/bin/bash

set -euo pipefail

# Default values
API_KEY=""
AGENT_VERSION=""
DEPLOYMENT_METHOD=""
CLUSTER_TYPE=""
CLUSTER_NAME="gpu-test-cluster"
NAMESPACE="datadog"
HELM_CHART_VERSION=""
OPERATOR_VERSION=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Test GPU check deployment configurations in Kubernetes

OPTIONS:
    -k, --api-key KEY           Datadog API key (required)
    -v, --agent-version VERSION Datadog agent version (required)
    -m, --method METHOD         Deployment method: helm|operator (required)
    -c, --cluster-type TYPE     Cluster type: uniform|mixed (required)
    -n, --cluster-name NAME     Cluster name (default: gpu-test-cluster)
    --namespace NAMESPACE       Kubernetes namespace (default: datadog)
    --helm-chart-version VER    Helm chart version (optional, defaults to latest)
    --operator-version VER      Datadog operator version (optional, defaults to latest)
    -h, --help                  Show this help message

EXAMPLES:
    $0 -k "your-api-key" -v "7.50.0" -m helm -c uniform
    $0 -k "your-api-key" -v "7.50.0" -m operator -c mixed
    $0 -k "your-api-key" -v "7.50.0" -m helm -c uniform --helm-chart-version "3.8.0"
    $0 -k "your-api-key" -v "7.50.0" -m operator -c mixed --operator-version "1.14.0"
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -k|--api-key)
                API_KEY="$2"
                shift 2
                ;;
            -v|--agent-version)
                AGENT_VERSION="$2"
                shift 2
                ;;
            -m|--method)
                DEPLOYMENT_METHOD="$2"
                shift 2
                ;;
            -c|--cluster-type)
                CLUSTER_TYPE="$2"
                shift 2
                ;;
            -n|--cluster-name)
                CLUSTER_NAME="$2"
                shift 2
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --helm-chart-version)
                HELM_CHART_VERSION="$2"
                shift 2
                ;;
            --operator-version)
                OPERATOR_VERSION="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Validate required parameters
validate_params() {
    local errors=0

    if [[ -z "$API_KEY" ]]; then
        log_error "API key is required"
        errors=$((errors + 1))
    fi

    if [[ -z "$AGENT_VERSION" ]]; then
        log_error "Agent version is required"
        errors=$((errors + 1))
    fi

    if [[ -z "$DEPLOYMENT_METHOD" ]]; then
        log_error "Deployment method is required"
        errors=$((errors + 1))
    elif [[ "$DEPLOYMENT_METHOD" != "helm" && "$DEPLOYMENT_METHOD" != "operator" ]]; then
        log_error "Deployment method must be 'helm' or 'operator'"
        errors=$((errors + 1))
    fi

    if [[ -z "$CLUSTER_TYPE" ]]; then
        log_error "Cluster type is required"
        errors=$((errors + 1))
    elif [[ "$CLUSTER_TYPE" != "uniform" && "$CLUSTER_TYPE" != "mixed" ]]; then
        log_error "Cluster type must be 'uniform' or 'mixed'"
        errors=$((errors + 1))
    fi

    if [[ $errors -gt 0 ]]; then
        usage
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing_tools=()

    if ! command -v nvkind &> /dev/null; then
        missing_tools+=("nvkind")
    fi

    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi

    if [[ "$DEPLOYMENT_METHOD" == "helm" ]] && ! command -v helm &> /dev/null; then
        missing_tools+=("helm")
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_error "Please install the missing tools before running this script"
        exit 1
    fi

    log_success "All prerequisites satisfied"
}

# Configure container runtime for GPU support
configure_container_runtime() {
    log_info "Configuring container runtime for GPU support..."

    # Configure NVIDIA Container Toolkit runtime
    if sudo nvidia-ctk runtime configure --runtime=docker --set-as-default --cdi.enabled; then
        log_success "NVIDIA Container Toolkit runtime configured"
    else
        log_error "Failed to configure NVIDIA Container Toolkit runtime"
        exit 1
    fi

    # Configure accept-nvidia-visible-devices-as-volume-mounts
    if sudo nvidia-ctk config --set accept-nvidia-visible-devices-as-volume-mounts=true --in-place; then
        log_success "NVIDIA Container Toolkit config updated"
    else
        log_error "Failed to update NVIDIA Container Toolkit config"
        exit 1
    fi

    # Restart Docker to apply changes
    log_info "Restarting Docker to apply changes..."
    if sudo systemctl restart docker; then
        log_success "Docker restarted successfully"
    else
        log_error "Failed to restart Docker"
        exit 1
    fi

    # Wait a moment for Docker to fully restart
    sleep 5

    # Verify Docker is running
    if sudo systemctl is-active --quiet docker; then
        log_success "Docker is running and ready"
    else
        log_error "Docker is not running after restart"
        exit 1
    fi

    log_success "Container runtime configuration completed"
}

# Create nvkind cluster
create_cluster() {
    log_info "Creating nvkind cluster: $CLUSTER_NAME"

    # Get script directory to find template
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local template_file="$script_dir/nvkind-config-template.yaml"
    local config_values="/tmp/${CLUSTER_NAME}-values.yaml"

    # Check if template exists
    if [[ ! -f "$template_file" ]]; then
        log_error "nvkind config template not found: $template_file"
        exit 1
    fi

    # Create cluster configuration values based on cluster type
    if [[ "$CLUSTER_TYPE" == "uniform" ]]; then
        log_info "Creating uniform cluster (single GPU node)"
        cat > "$config_values" << EOF
name: $CLUSTER_NAME
workers:
- devices: all
EOF
    else
        log_info "Creating mixed cluster (one GPU node, one non-GPU node)"
        cat > "$config_values" << EOF
name: $CLUSTER_NAME
workers:
- devices: all
- {}
EOF
    fi

    # Create the cluster using the template
    if nvkind create cluster --config-template "$template_file" --config-values "$config_values"; then
        log_success "Cluster created successfully"
    else
        log_error "Failed to create cluster"
        exit 1
    fi

    # Clean up config values file
    rm -f "$config_values"

    # Wait for cluster to be ready
    log_info "Waiting for cluster to be ready..."
    kubectl wait --for=condition=Ready nodes --all --timeout=300s

    log_success "Cluster is ready"
}

# Install NVIDIA GPU Operator
install_nvidia_gpu_operator() {
    log_info "Installing NVIDIA GPU Operator..."

    # Add NVIDIA Helm repository
    helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
    helm repo update

    # Create namespace for GPU operator
    kubectl create namespace gpu-operator --dry-run=client -o yaml | kubectl apply -f -

    # Install NVIDIA GPU Operator
    if helm upgrade --install gpu-operator nvidia/gpu-operator \
        --namespace gpu-operator \
        --set operator.defaultRuntime=containerd \
        --wait --timeout=600s; then
        log_success "NVIDIA GPU Operator installed successfully"
    else
        log_error "Failed to install NVIDIA GPU Operator"
        exit 1
    fi

    # Wait for GPU operator pods to be ready
    log_info "Waiting for GPU operator pods to be ready..."
    kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=gpu-operator -n gpu-operator --timeout=600s

    # Wait for GPU nodes to be labeled
    log_info "Waiting for GPU nodes to be properly labeled..."
    local max_attempts=30
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if kubectl get nodes -l nvidia.com/gpu.present=true --no-headers | grep -q .; then
            log_success "GPU nodes are properly labeled"
            break
        fi

        attempt=$((attempt + 1))
        log_info "Attempt $attempt/$max_attempts: Waiting for GPU node labels..."
        sleep 10
    done

    if [[ $attempt -eq $max_attempts ]]; then
        log_warning "GPU nodes may not be properly labeled yet, continuing anyway..."
    fi

    log_success "NVIDIA GPU Operator installation completed"
}

# Helper function to deploy Datadog with a specific template
_deploy_datadog_helm() {
    local template_name="$1"
    local release_name="$2"
    local description="$3"

    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local values_template="$script_dir/$template_name"
    local values_file="/tmp/datadog-values-$release_name.yaml"

    log_info "Deploying $description..."

    # Check if template exists
    if [[ ! -f "$values_template" ]]; then
        log_error "Helm values template not found: $values_template"
        exit 1
    fi

    # Substitute variables in the template
    envsubst < "$values_template" > "$values_file"

    # Install Datadog
    local helm_cmd="helm upgrade --install $release_name datadog/datadog --namespace $NAMESPACE --values $values_file --wait --timeout=600s"

    # Add version flag if specified
    if [[ -n "$HELM_CHART_VERSION" ]]; then
        helm_cmd="$helm_cmd --version $HELM_CHART_VERSION"
    fi

    if eval "$helm_cmd"; then
        log_success "Datadog installed successfully for $description"
    else
        log_error "Failed to install Datadog for $description"
        exit 1
    fi

    # Clean up values file
    rm -f "$values_file"
}

# Install Datadog using Helm
install_datadog_helm() {
    log_info "Installing Datadog using Helm..."

    # Add Datadog Helm repository
    helm repo add datadog https://helm.datadoghq.com
    helm repo update

    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

    if [[ "$CLUSTER_TYPE" == "uniform" ]]; then
        _deploy_datadog_helm "helm-uniform.yaml" "datadog" "uniform cluster"
    else
        log_info "Deploying for mixed cluster (two separate deployments)..."
        _deploy_datadog_helm "helm-mixed-non-gpu.yaml" "datadog" "non-GPU nodes"
        _deploy_datadog_helm "helm-mixed-gpu.yaml" "datadog-gpu" "GPU nodes"
    fi
}

# Helper function to deploy DatadogAgent with a specific template
_deploy_datadog_operator() {
    local template_name="$1"
    local description="$2"

    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local datadogagent_template="$script_dir/$template_name"
    local datadogagent_file="/tmp/datadogagent-$(basename "$template_name" .yaml).yaml"

    log_info "Deploying $description..."

    # Check if template exists
    if [[ ! -f "$datadogagent_template" ]]; then
        log_error "DatadogAgent template not found: $datadogagent_template"
        exit 1
    fi

    # Substitute variables in the template
    envsubst < "$datadogagent_template" > "$datadogagent_file"

    # Apply DatadogAgent resource(s)
    if kubectl apply -f "$datadogagent_file"; then
        log_success "DatadogAgent resource(s) created for $description"
    else
        log_error "Failed to create DatadogAgent resource(s) for $description"
        exit 1
    fi

    # Clean up manifest file
    rm -f "$datadogagent_file"
}

# Install Datadog using Operator
install_datadog_operator() {
    log_info "Installing Datadog using Operator..."

    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

    # Install Datadog Operator
    local operator_url="https://github.com/DataDog/datadog-operator/releases/latest/download/datadog-operator.yaml"

    # Use specific version if specified
    if [[ -n "$OPERATOR_VERSION" ]]; then
        operator_url="https://github.com/DataDog/datadog-operator/releases/download/v${OPERATOR_VERSION}/datadog-operator.yaml"
    fi

    kubectl apply -f "$operator_url"

    # Wait for operator to be ready
    kubectl wait --for=condition=Available deployment/datadog-operator -n datadog-operator-system --timeout=300s

    if [[ "$CLUSTER_TYPE" == "uniform" ]]; then
        _deploy_datadog_operator "operator-uniform.yaml" "uniform cluster"
    else
        _deploy_datadog_operator "operator-mixed.yaml" "mixed cluster (using DatadogAgentProfile)"
    fi

    # Wait for pods to be ready
    log_info "Waiting for Datadog pods to be ready..."
    kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=datadog -n "$NAMESPACE" --timeout=600s

    log_success "Datadog installed successfully via Operator"
}

# Validate deployment (placeholder)
validate_deployment() {
    log_info "Validating deployment..."

    # TODO: Implement comprehensive validation
    # This is placeholder code as requested

    log_info "Checking Datadog pods status..."
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=datadog

    log_info "Checking GPU nodes..."
    kubectl get nodes -l gpu=nvidia -o wide

    log_info "Checking GPU resources..."
    kubectl describe nodes -l gpu=nvidia | grep -A 5 "Allocatable:"

    # Placeholder validation checks
    log_warning "Validation logic is placeholder - implement actual checks:"
    log_warning "- Verify GPU metrics are being collected"
    log_warning "- Check agent logs for GPU monitoring status"
    log_warning "- Validate GPU resource allocation"
    log_warning "- Test metric submission to Datadog"

    log_success "Basic deployment validation completed"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."

    if nvkind get clusters | grep -q "$CLUSTER_NAME"; then
        log_info "Deleting cluster: $CLUSTER_NAME"
        nvkind delete cluster --name "$CLUSTER_NAME"
    fi

    log_success "Cleanup completed"
}

# Main execution
main() {
    log_info "Starting GPU deployment test..."
    log_info "Parameters: API_KEY=<redacted>, AGENT_VERSION=$AGENT_VERSION, METHOD=$DEPLOYMENT_METHOD, CLUSTER_TYPE=$CLUSTER_TYPE"
    log_info "Chart/Operator versions: HELM_CHART_VERSION=${HELM_CHART_VERSION:-latest}, OPERATOR_VERSION=${OPERATOR_VERSION:-latest}"

    # Set up cleanup trap
    trap cleanup EXIT

        check_prerequisites
    configure_container_runtime
    create_cluster
    install_nvidia_gpu_operator

    if [[ "$DEPLOYMENT_METHOD" == "helm" ]]; then
        install_datadog_helm
    else
        install_datadog_operator
    fi

    validate_deployment

    log_success "GPU deployment test completed successfully!"
    log_info "Cluster '$CLUSTER_NAME' is ready for further testing"
    log_info "Use 'kubectl config use-context kind-$CLUSTER_NAME' to interact with the cluster"
}

# Parse arguments and run main function
parse_args "$@"
validate_params
main
