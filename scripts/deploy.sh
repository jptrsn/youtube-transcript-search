#!/bin/bash

set -e

REMOTE_HOST="${REMOTE_HOST}"
REMOTE_PATH="${REMOTE_PATH:-/opt/youtube-transcript-search}"

echo "🚀 Deploying to ${REMOTE_HOST}..."

# Step 1: Build images locally (optional, for testing)
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.prod.yml build

# Step 2: Copy files to remote server
echo "📤 Copying files to remote server..."
rsync -avz --exclude 'node_modules' \
    --exclude 'venv' \
    --exclude '.git' \
    --exclude 'postgres_data' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    ./ ${REMOTE_HOST}:${REMOTE_PATH}/

# Step 3: Copy .env file separately (if needed)
echo "📋 Copying environment file..."
scp .env.prod ${REMOTE_HOST}:${REMOTE_PATH}/.env

# Step 4: Deploy on remote server
echo "🐳 Starting services on remote server..."
ssh ${REMOTE_HOST} << EOF
    cd ${REMOTE_PATH}
    docker-compose -f docker-compose.prod.yml pull
    docker-compose -f docker-compose.prod.yml up -d --build
    docker-compose -f docker-compose.prod.yml ps
EOF

echo "✅ Deployment complete!"