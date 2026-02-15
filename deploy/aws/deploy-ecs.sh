#!/bin/bash
# ClawShell ECS Deployment Script
# Usage: ./deploy-ecs.sh [environment]

set -euo pipefail

# Configuration
ENVIRONMENT="${1:-production}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="clawshell-proxy"
ECS_CLUSTER="clawshell-cluster"
ECS_SERVICE="clawshell-proxy-service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    command -v aws >/dev/null 2>&1 || { log_error "AWS CLI is required but not installed."; exit 1; }
    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed."; exit 1; }
    command -v jq >/dev/null 2>&1 || { log_error "jq is required but not installed."; exit 1; }

    # Check AWS credentials
    aws sts get-caller-identity >/dev/null 2>&1 || { log_error "AWS credentials not configured."; exit 1; }

    log_info "Prerequisites OK"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."

    cd "$(dirname "$0")/../proxy"

    docker build \
        -f Dockerfile.production \
        -t "${ECR_REPOSITORY}:${ENVIRONMENT}" \
        -t "${ECR_REPOSITORY}:latest" \
        --build-arg ENVIRONMENT="${ENVIRONMENT}" \
        .

    log_info "Docker image built successfully"
}

# Push to ECR
push_to_ecr() {
    log_info "Pushing to ECR..."

    # Get ECR registry URI
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

    # Login to ECR
    aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

    # Create repository if it doesn't exist
    aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" >/dev/null 2>&1 || \
        aws ecr create-repository --repository-name "${ECR_REPOSITORY}" --region "${AWS_REGION}"

    # Tag and push
    docker tag "${ECR_REPOSITORY}:${ENVIRONMENT}" "${ECR_REGISTRY}/${ECR_REPOSITORY}:${ENVIRONMENT}"
    docker tag "${ECR_REPOSITORY}:latest" "${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"

    docker push "${ECR_REGISTRY}/${ECR_REPOSITORY}:${ENVIRONMENT}"
    docker push "${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"

    log_info "Image pushed to ECR: ${ECR_REGISTRY}/${ECR_REPOSITORY}:${ENVIRONMENT}"
}

# Update ECS task definition
update_task_definition() {
    log_info "Updating ECS task definition..."

    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

    # Substitute variables in task definition
    TASK_DEF=$(cat "$(dirname "$0")/ecs-task-definition.json" | \
        sed "s|\${AWS_ACCOUNT_ID}|${ACCOUNT_ID}|g" | \
        sed "s|\${AWS_REGION}|${AWS_REGION}|g" | \
        sed "s|\${ECR_REPOSITORY_URI}|${ECR_REGISTRY}/${ECR_REPOSITORY}|g")

    # Register task definition
    TASK_DEF_ARN=$(aws ecs register-task-definition \
        --cli-input-json "${TASK_DEF}" \
        --region "${AWS_REGION}" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)

    log_info "Task definition registered: ${TASK_DEF_ARN}"

    echo "${TASK_DEF_ARN}"
}

# Deploy to ECS
deploy_to_ecs() {
    local TASK_DEF_ARN="$1"

    log_info "Deploying to ECS..."

    # Update service with new task definition
    aws ecs update-service \
        --cluster "${ECS_CLUSTER}" \
        --service "${ECS_SERVICE}" \
        --task-definition "${TASK_DEF_ARN}" \
        --force-new-deployment \
        --region "${AWS_REGION}"

    log_info "Deployment initiated"

    # Wait for service stability
    log_info "Waiting for service stability..."
    aws ecs wait services-stable \
        --cluster "${ECS_CLUSTER}" \
        --services "${ECS_SERVICE}" \
        --region "${AWS_REGION}"

    log_info "Deployment completed successfully!"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Get running tasks
    RUNNING_TASKS=$(aws ecs list-tasks \
        --cluster "${ECS_CLUSTER}" \
        --service-name "${ECS_SERVICE}" \
        --desired-status RUNNING \
        --region "${AWS_REGION}" \
        --query 'taskArns' \
        --output json | jq 'length')

    if [ "${RUNNING_TASKS}" -gt 0 ]; then
        log_info "✓ ${RUNNING_TASKS} tasks running"
    else
        log_error "No running tasks found!"
        exit 1
    fi

    # Check health status
    HEALTH_STATUS=$(aws ecs describe-services \
        --cluster "${ECS_CLUSTER}" \
        --services "${ECS_SERVICE}" \
        --region "${AWS_REGION}" \
        --query 'services[0].healthStatus' \
        --output text)

    log_info "Service health status: ${HEALTH_STATUS}"

    if [ "${HEALTH_STATUS}" = "HEALTHY" ]; then
        log_info "✓ Service is healthy"
    else
        log_warn "Service health status: ${HEALTH_STATUS}"
    fi
}

# Rollback function
rollback() {
    local PREVIOUS_REVISION="$1"

    if [ -z "${PREVIOUS_REVISION}" ]; then
        log_error "No previous revision specified for rollback"
        exit 1
    fi

    log_warn "Rolling back to revision ${PREVIOUS_REVISION}..."

    aws ecs update-service \
        --cluster "${ECS_CLUSTER}" \
        --service "${ECS_SERVICE}" \
        --task-definition "clawshell-proxy:${PREVIOUS_REVISION}" \
        --region "${AWS_REGION}"

    log_info "Rollback initiated"
}

# Main deployment flow
main() {
    log_info "Starting ClawShell deployment (${ENVIRONMENT})"

    check_prerequisites
    build_image
    push_to_ecr
    TASK_DEF_ARN=$(update_task_definition)
    deploy_to_ecs "${TASK_DEF_ARN}"
    verify_deployment

    log_info "Deployment complete!"
}

# Handle command line arguments
case "${1:-}" in
    rollback)
        rollback "${2:-}"
        ;;
    *)
        main
        ;;
esac
