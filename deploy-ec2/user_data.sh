#!/bin/bash
set -e

# Install Docker (supports ARM64 on Amazon Linux 2023)
yum update -y
yum install -y docker git
systemctl enable docker
systemctl start docker

# Install Docker Compose v2 for ARM64
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Allow ec2-user to run docker without sudo
usermod -aG docker ec2-user

# Create app directory — code will be synced here by deploy3.sh
mkdir -p /home/ec2-user/luminx
chown ec2-user:ec2-user /home/ec2-user/luminx

# Pre-pull python:3.11-slim for arm64 to speed up first build
docker pull --platform linux/arm64 python:3.11-slim || true
