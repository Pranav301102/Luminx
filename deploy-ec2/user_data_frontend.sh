#!/bin/bash
set -e

yum update -y
yum install -y nginx rsync

systemctl enable nginx

mkdir -p /usr/share/nginx/luminx
chown ec2-user:ec2-user /usr/share/nginx/luminx
