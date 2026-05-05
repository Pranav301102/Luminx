#!/bin/bash
# Usage: ./deploy.sh <path-to-pem-key>
set -e

KEY="${1:?Usage: ./deploy.sh <path-to-pem-key>}"
TF_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$TF_DIR/.." && pwd)"
SSH_OPTS="-i $KEY -o StrictHostKeyChecking=no"

# ── Get IPs from Terraform output ────────────────────────────────────────────
HEAD_IP=$(terraform -chdir="$TF_DIR" output -raw head_ip)
TAIL_IP=$(terraform -chdir="$TF_DIR" output -raw tail_ip)
FRONTEND_IP=$(terraform -chdir="$TF_DIR" output -raw frontend_ip)

echo "Head (Node A + Tracker) : $HEAD_IP"
echo "Tail (Node B)           : $TAIL_IP"
echo "Frontend                : $FRONTEND_IP"
echo ""

RSYNC="rsync -az --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
  --exclude='.pytest_cache' --exclude='deploy-ec2' --exclude='terraform' \
  --exclude='lumina-frontend-main' --exclude='sprint1' \
  -e 'ssh $SSH_OPTS'"

# ── Deploy Head (Node A + Tracker) ───────────────────────────────────────────
echo ">>> Deploying Head instance ($HEAD_IP)..."
eval "$RSYNC $PROJECT/ ec2-user@$HEAD_IP:/home/ec2-user/luminx/"
ssh $SSH_OPTS ec2-user@$HEAD_IP "
  cd /home/ec2-user/luminx
  NODE_B_HOST=$TAIL_IP docker compose -f docker-compose.head.yml up -d --build
"
echo "Head deployed."

# ── Deploy Tail (Node B) ──────────────────────────────────────────────────────
echo ""
echo ">>> Deploying Tail instance ($TAIL_IP)..."
eval "$RSYNC $PROJECT/ ec2-user@$TAIL_IP:/home/ec2-user/luminx/"
ssh $SSH_OPTS ec2-user@$TAIL_IP "
  cd /home/ec2-user/luminx
  TRACKER_HOST=$HEAD_IP docker compose -f docker-compose.tail.yml up -d --build
"
echo "Tail deployed."

# ── Build & Deploy Frontend ───────────────────────────────────────────────────
echo ""
echo ">>> Building frontend..."
cd "$PROJECT/lumina-frontend-main"
VITE_API_BASE_URL=http://$HEAD_IP:8001 \
VITE_TRACKER_BASE_URL=http://$HEAD_IP:8003 \
  npm run build

echo ">>> Deploying frontend to $FRONTEND_IP..."
rsync -az -e "ssh $SSH_OPTS" dist/ ec2-user@$FRONTEND_IP:/usr/share/nginx/luminx/

# Configure nginx on frontend instance
ssh $SSH_OPTS ec2-user@$FRONTEND_IP "
sudo tee /etc/nginx/conf.d/luminx.conf > /dev/null << 'EOF'
server {
    listen 80;
    root /usr/share/nginx/luminx;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
sudo nginx -t && sudo systemctl restart nginx
"
echo "Frontend deployed."

echo ""
echo "========================================"
echo "Deployment complete!"
echo "========================================"
echo ""
echo "Frontend  : http://$FRONTEND_IP"
echo "Generate  : http://$HEAD_IP:8001/generate"
echo "Tracker   : http://$HEAD_IP:8003/assignment"
echo ""
echo "Logs:"
echo "  Head  : ssh $SSH_OPTS ec2-user@$HEAD_IP 'cd luminx && docker compose -f docker-compose.head.yml logs -f'"
echo "  Tail  : ssh $SSH_OPTS ec2-user@$TAIL_IP 'cd luminx && docker compose -f docker-compose.tail.yml logs -f'"
