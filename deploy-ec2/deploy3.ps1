param(
    [Parameter(Mandatory=$true)][string]$KeyPath,
    [Parameter(Mandatory=$true)][string]$LocalIp
)

$ErrorActionPreference = "Stop"

$TfDir = $PSScriptRoot
$ProjectDir = (Resolve-Path "$TfDir\..").Path

Write-Host "Applying Terraform changes..."
terraform -chdir="$TfDir" apply -var="key_pair_name=luminx-key" -auto-approve

Write-Host "Getting Terraform outputs..."
$cloud1_ip = terraform -chdir="$TfDir" output -raw cloud1_ip
$cloud2_ip = terraform -chdir="$TfDir" output -raw cloud2_ip

if (-not $cloud1_ip -or $cloud1_ip -match "No outputs found") {
    Write-Error "Terraform outputs not found. Did you run terraform apply?"
}

Write-Host "Cloud 1: $cloud1_ip"
Write-Host "Cloud 2: $cloud2_ip"
Write-Host "Local Node B: ${LocalIp}:8002"

Write-Host "Building React frontend..."
Set-Location "$ProjectDir\lumina-frontend-main"
$env:VITE_API_BASE_URL = "http://${cloud1_ip}:8001"
$env:VITE_TRACKER_BASE_URL = "http://${cloud1_ip}:8003"
npm install
npm run build

Write-Host "Packaging project..."
Set-Location $ProjectDir
# Use Windows 10/11 built-in tar.exe to avoid WSL/rsync complexities
tar.exe -czf project.tar.gz --exclude=project.tar.gz `
    --exclude=venv --exclude=__pycache__ --exclude=.git `
    --exclude=.pytest_cache --exclude=deploy-ec2 --exclude=terraform `
    --exclude=lumina-frontend-main/node_modules --exclude=sprint1 .

$SshKey = Resolve-Path $KeyPath
$SshOpts = "-i", $SshKey, "-o", "StrictHostKeyChecking=no"

Write-Host "Deploying to Cloud 1 ($cloud1_ip)..."
scp -i "$SshKey" -o StrictHostKeyChecking=no project.tar.gz "ec2-user@${cloud1_ip}:/home/ec2-user/project.tar.gz"
ssh -i "$SshKey" -o StrictHostKeyChecking=no ec2-user@${cloud1_ip} "sudo curl -SL 'https://github.com/docker/buildx/releases/download/v0.17.1/buildx-v0.17.1.linux-arm64' -o /usr/local/lib/docker/cli-plugins/docker-buildx && sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx && rm -rf luminx && mkdir -p luminx && tar -xzf project.tar.gz -C luminx && rm project.tar.gz && cd luminx && export NODE_B_URL=http://${LocalIp}:8002 && export NODE_C_URL=http://${cloud2_ip}:8004 && docker compose -f docker-compose.cloud1.yml up -d --build"

Write-Host "Deploying to Cloud 2 ($cloud2_ip)..."
scp -i "$SshKey" -o StrictHostKeyChecking=no project.tar.gz "ec2-user@${cloud2_ip}:/home/ec2-user/project.tar.gz"
ssh -i "$SshKey" -o StrictHostKeyChecking=no ec2-user@${cloud2_ip} "sudo curl -SL 'https://github.com/docker/buildx/releases/download/v0.17.1/buildx-v0.17.1.linux-arm64' -o /usr/local/lib/docker/cli-plugins/docker-buildx && sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx && rm -rf luminx && mkdir -p luminx && tar -xzf project.tar.gz -C luminx && rm project.tar.gz && cd luminx && export TRACKER_URL=http://${cloud1_ip}:8003 && docker compose -f docker-compose.cloud2.yml up -d --build"

Write-Host "Cleaning up local archive..."
Remove-Item project.tar.gz

Write-Host "Deployment complete!"
Write-Host "================================================"
Write-Host "Your Frontend is available at: http://${cloud1_ip}"
Write-Host "================================================"
Write-Host ""
Write-Host "Next step - start Node B on your LOCAL machine natively:"
Write-Host "Run the following commands in your PowerShell:"
Write-Host ""
Write-Host "`$env:MODEL_NAME=`"microsoft/Phi-4-mini-instruct`""
Write-Host "`$env:SPLIT_LAYER_A=`"10`""
Write-Host "`$env:SPLIT_LAYER_B=`"21`""
Write-Host "`$env:SPLIT_LAYER=`"10`""
Write-Host "`$env:NODE_C_URL=`"http://${cloud2_ip}:8004`""
Write-Host "`$env:TRACKER_URL=`"http://${cloud1_ip}:8003`""
Write-Host "`$env:ENABLE_DYNAMIC_SPLIT=`"true`""
Write-Host "`$env:NODE_B_ID=`"node-b`""
Write-Host ".\venv\Scripts\python -m uvicorn node_b:app --host 0.0.0.0 --port 8002"
Write-Host ""
