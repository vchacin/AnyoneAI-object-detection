#!/bin/bash
set -euo pipefail
cd /opt/shelfvision
set -a
source .env
set +a
registry="${BACKEND_IMAGE%%/*}"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$registry"
docker compose pull
docker compose up -d --wait --wait-timeout 240
