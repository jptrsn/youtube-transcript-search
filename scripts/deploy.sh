#!/bin/bash

set -e

# Load production env for remote host info
if [ -f .env.prod ]; then
    export $(cat .env.prod | grep -v '^#' | xargs)
fi

REMOTE_HOST="${REMOTE_HOST}"
REMOTE_PATH="${REMOTE_PATH:-/opt/youtube-transcript-search}"

echo "🚀 Deploying to ${REMOTE_HOST}..."

# Step 1: Copy files to remote server
echo "📤 Copying files to remote server..."
rsync -avz --exclude 'node_modules' \
    --exclude 'venv' \
    --exclude '.git' \
    --exclude 'postgres_data' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude '.env.prod' \
    --exclude 'db_backup_*.sql' \
    ./ ${REMOTE_HOST}:${REMOTE_PATH}/

# Step 2: Copy .env.prod as .env on remote
echo "📋 Copying environment file..."
scp .env.prod ${REMOTE_HOST}:${REMOTE_PATH}/.env

# Step 3: Deploy on remote server
echo "🐳 Starting services on remote server..."
ssh ${REMOTE_HOST} << 'EOF'
    cd /opt/youtube-transcript-search

    # Pull latest images
    docker compose -f docker-compose.prod.yml pull

    # Build and start services
    docker compose -f docker-compose.prod.yml up -d --build

    # Run migrations
    docker compose -f docker-compose.prod.yml exec -T backend python3 -m alembic upgrade head

    # Show running services
    docker compose -f docker-compose.prod.yml ps
EOF

echo "✅ Deployment complete!"
echo "🌐 Your app should be available at: https://ytscri.be"