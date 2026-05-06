#!/bin/bash
# 3-node deployment script for Luminx
# Usage: ./deploy3.sh <path-to-pem-key> <local-machine-public-ip>
#
# What it does:
#   1. Deploys Cloud 1 (Node A + Tracker) via rsync + docker compose
#   2. Deploys Cloud 2 (Node C) via rsync + docker compose
#   3. Builds the React frontend and uploads it to S3 + invalidates CloudFront
#
# After this script:
#   - Start Node B on your local machine:
#       TRACKER_URL=http://<cloud1_ip>:8003 \
#       NODE_C_URL=http://<cloud2_ip>:8004 \
#       docker compose -f docker-compose.local.yml up -d --build
#   - Make sure port 8002 is forwarded on your router to this machine's LAN IP.
set -e

KEY="${1:?Usage: ./deploy3.sh <path-to-pem-key> <local-machine-public-ip>}"
LOCAL_IP="${2:?Usage: ./deploy3.sh <path-to-pem-key> <local-machine-public-ip>}"

TF_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$TF_DIR/.." && pwd)"
SSH_OPTS="-i $KEY -o StrictHostKeyChecking=no"

# ── Get IPs and S3/CF IDs from Terraform output ───────────────────────────────
CLOUD1_IP=$(terraform -chdir="$TF_DIR" output -raw cloud1_ip)
CLOUD2_IP=$(terraform -chdir="$TF_DIR" output -raw cloud2_ip)
CF_BUCKET=$(terraform -chdir="$TF_DIR" output -raw frontend_bucket)
CF_ID=$(terraform -chdir="$TF_DIR" output -raw cloudfront_id)

echo "Cloud 1 (Node A + Tracker) : $CLOUD1_IP"
echo "Cloud 2 (Node C)           : $CLOUD2_IP"
echo "Local Node B               : $LOCAL_IP:8002"
echo "S3 bucket                  : $CF_BUCKET"
echo ""

RSYNC="rsync -az \
  --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
  --exclude='.pytest_cache' --exclude='deploy-ec2' --exclude='terraform' \
  --exclude='lumina-frontend-main' --exclude='sprint1' \
  -e 'ssh $SSH_OPTS'"

# ── Deploy Cloud 1 (Node A + Tracker) ────────────────────────────────────────
echo ">>> Deploying Cloud 1 ($CLOUD1_IP) — Node A + Tracker..."
eval "$RSYNC $PROJECT/ ec2-user@$CLOUD1_IP:/home/ec2-user/luminx/"
ssh $SSH_OPTS ec2-user@$CLOUD1_IP "
  cd /home/ec2-user/luminx
  NODE_B_URL=http://$LOCAL_IP:8002 \
  NODE_C_URL=http://$CLOUD2_IP:8004 \
  docker compose -f docker-compose.cloud1.yml up -d --build
"
echo "Cloud 1 deployed."

# ── Deploy Cloud 2 (Node C) ───────────────────────────────────────────────────
echo ""
echo ">>> Deploying Cloud 2 ($CLOUD2_IP) — Node C..."
eval "$RSYNC $PROJECT/ ec2-user@$CLOUD2_IP:/home/ec2-user/luminx/"
ssh $SSH_OPTS ec2-user@$CLOUD2_IP "
  cd /home/ec2-user/luminx
  TRACKER_URL=http://$CLOUD1_IP:8003 \
  docker compose -f docker-compose.cloud2.yml up -d --build
"
echo "Cloud 2 deployed."

# ── Build & upload frontend ───────────────────────────────────────────────────
echo ""
echo ">>> Building frontend (API → Cloud 1)..."
cd "$PROJECT/lumina-frontend-main"
VITE_API_BASE_URL=http://$CLOUD1_IP:8001 \
VITE_TRACKER_BASE_URL=http://$CLOUD1_IP:8003 \
  npm run build

echo ">>> Uploading frontend to S3 (s3://$CF_BUCKET/)..."
aws s3 sync dist/ "s3://$CF_BUCKET/" --delete

echo ">>> Invalidating CloudFront cache ($CF_ID)..."
aws cloudfront create-invalidation \
  --distribution-id "$CF_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text

echo ""
echo "========================================"
echo "Deployment complete!"
echo "========================================"
echo ""
echo "Endpoints:"
echo "  Frontend  : https://$(terraform -chdir="$TF_DIR" output -raw cloudfront_url 2>/dev/null || echo '<cloudfront_url>')"
echo "  Generate  : http://$CLOUD1_IP:8001/generate"
echo "  Tracker   : http://$CLOUD1_IP:8003/assignment"
echo ""
echo "Next step — start Node B on your LOCAL machine:"
echo "  TRACKER_URL=http://$CLOUD1_IP:8003 \\"
echo "  NODE_C_URL=http://$CLOUD2_IP:8004 \\"
echo "  docker compose -f docker-compose.local.yml up -d --build"
echo ""
echo "  Also ensure port 8002 is forwarded on your router → this machine."
echo ""
echo "Logs:"
echo "  Cloud 1 : ssh $SSH_OPTS ec2-user@$CLOUD1_IP 'cd luminx && docker compose -f docker-compose.cloud1.yml logs -f'"
echo "  Cloud 2 : ssh $SSH_OPTS ec2-user@$CLOUD2_IP 'cd luminx && docker compose -f docker-compose.cloud2.yml logs -f'"
