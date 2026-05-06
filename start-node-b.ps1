#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Starts local Node B and creates a localtunnel, then automatically
    updates Cloud 1's NODE_B_URL so Node A can reach it. Run this instead
    of starting Node B and the SSH tunnel manually.

.EXAMPLE
    .\start-node-b.ps1 -KeyPath ~/.ssh/luminx-key.pem
#>
param(
    [string]$KeyPath = "~/.ssh/luminx-key.pem",
    [string]$Cloud1Ip = "18.236.230.66",
    [string]$Cloud2Ip = "18.246.165.53"
)

$ErrorActionPreference = "Stop"
$ProjectDir = (Resolve-Path "$PSScriptRoot").Path

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  LuminX Local Node B Launcher" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# ── 1. Start localtunnel in background ───────────────────────────────────────
Write-Host "`n[1/4] Starting localtunnel on port 8002..." -ForegroundColor Yellow
$ltJob = Start-Job -ScriptBlock {
    npx -y localtunnel --port 8002 2>&1
}

# Wait for the tunnel URL to appear
Write-Host "      Waiting for tunnel URL..." -ForegroundColor Gray
$tunnelUrl = $null
$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline -and -not $tunnelUrl) {
    Start-Sleep -Milliseconds 500
    $output = Receive-Job $ltJob -Keep
    foreach ($line in ($output -split "`n")) {
        if ($line -match "your url is: (https://\S+)") {
            $tunnelUrl = $matches[1].Trim()
            break
        }
    }
}

if (-not $tunnelUrl) {
    Write-Error "Failed to get tunnel URL within 30s. Is localtunnel installed? Run: npm install -g localtunnel"
}

Write-Host "      Tunnel URL: $tunnelUrl" -ForegroundColor Green

# ── 2. Update docker-compose.cloud1.yml on EC2 ───────────────────────────────
Write-Host "`n[2/4] Updating NODE_B_URL on Cloud 1 ($Cloud1Ip)..." -ForegroundColor Yellow
$remoteCompose = "/home/ec2-user/luminx/docker-compose.cloud1.yml"

ssh -i $KeyPath -o StrictHostKeyChecking=no ec2-user@$Cloud1Ip `
    "sed -i 's|NODE_B_URL=.*|NODE_B_URL=$tunnelUrl|g' $remoteCompose"

Write-Host "      Updated NODE_B_URL => $tunnelUrl" -ForegroundColor Green

# ── 3. Restart only Node A (no full rebuild) ─────────────────────────────────
Write-Host "`n[3/4] Restarting Node A on Cloud 1 to pick up new URL..." -ForegroundColor Yellow
ssh -i $KeyPath -o StrictHostKeyChecking=no ec2-user@$Cloud1Ip `
    "cd luminx; docker compose -f docker-compose.cloud1.yml up -d"

Write-Host "      Node A restarting (model load takes ~2 min)..." -ForegroundColor Green

# ── 4. Start local Node B ────────────────────────────────────────────────────
Write-Host "`n[4/4] Starting local Node B..." -ForegroundColor Yellow
Write-Host "      Press Ctrl+C to stop Node B and the tunnel.`n" -ForegroundColor Gray

Set-Location $ProjectDir

$env:MODEL_NAME        = "microsoft/Phi-4-mini-instruct"
$env:SPLIT_LAYER_A     = "10"
$env:SPLIT_LAYER_B     = "21"
$env:SPLIT_LAYER       = "10"
$env:NODE_C_URL        = "http://${Cloud2Ip}:8004"
$env:TRACKER_URL       = "http://${Cloud1Ip}:8003"
$env:ENABLE_DYNAMIC_SPLIT = "true"
$env:NODE_B_ID         = "node-b"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Frontend: http://$Cloud1Ip" -ForegroundColor Green
Write-Host "  Node B tunnel: $tunnelUrl" -ForegroundColor Green
Write-Host "================================================`n" -ForegroundColor Cyan

try {
    .\venv\Scripts\python -m uvicorn node_b:app --host 0.0.0.0 --port 8002
} finally {
    Write-Host "`nStopping localtunnel..." -ForegroundColor Yellow
    Stop-Job $ltJob -ErrorAction SilentlyContinue
    Remove-Job $ltJob -ErrorAction SilentlyContinue
}
