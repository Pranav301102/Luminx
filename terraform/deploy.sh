#!/usr/bin/env bash
# Usage: ./deploy.sh [dev|staging|prod]
# Builds Docker images, pushes to ECR, then applies Terraform.
set -euo pipefail

ENV="${1:-dev}"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "==> Deploying env=${ENV} to ${REGISTRY}"

# ── 1. Terraform init + apply (creates ECR repos if they don't exist) ─────────
cd "$(dirname "$0")"
terraform init -input=false
terraform apply -auto-approve -var="environment=${ENV}" -var="aws_region=${REGION}"

# ── 2. Docker login to ECR ────────────────────────────────────────────────────
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${REGISTRY}"

# ── 3. Build + push each image ────────────────────────────────────────────────
cd ..
TAG="${ENV}-$(git rev-parse --short HEAD)"

for SERVICE in tracker node-a node-b; do
  REPO="${REGISTRY}/luminx/${SERVICE}"
  echo "==> Building ${SERVICE}:${TAG}"
  docker build -f docker/Dockerfile -t "${REPO}:${TAG}" -t "${REPO}:latest" .
  docker push "${REPO}:${TAG}"
  docker push "${REPO}:latest"
done

# ── 4. Force ECS to redeploy with the new images ──────────────────────────────
CLUSTER="luminx-${ENV}"
for SERVICE in tracker node-b node-a; do
  echo "==> Redeploying ECS service luminx-${SERVICE}"
  aws ecs update-service \
    --cluster "${CLUSTER}" \
    --service "luminx-${SERVICE}" \
    --force-new-deployment \
    --region "${REGION}" \
    --output text --query 'service.serviceName' > /dev/null
done

echo ""
echo "==> Done. Endpoint:"
cd terraform
terraform output -raw generate_endpoint
echo ""
