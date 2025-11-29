#!/bin/bash

# Script to migrate local database to remote server via SSH

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Load production environment for remote details
if [ -f .env.prod ]; then
    export $(cat .env.prod | grep -v '^#' | xargs)
fi

# Configuration
LOCAL_DB_CONTAINER="yt-transcript-db-local"
LOCAL_DB_NAME="${POSTGRES_DB:-youtube_transcripts}"
LOCAL_DB_USER="${POSTGRES_USER:-ytuser}"
REMOTE_HOST="${REMOTE_HOST}"
REMOTE_PATH="/opt/youtube-transcript-search"
BACKUP_FILE="db_backup_$(date +%Y%m%d_%H%M%S).sql"

echo "🔄 Starting database migration process..."

echo "📦 Creating backup of local database..."
docker exec ${LOCAL_DB_CONTAINER} pg_dump -U ${LOCAL_DB_USER} ${LOCAL_DB_NAME} > ${BACKUP_FILE}

echo "✅ Backup created: ${BACKUP_FILE}"

echo "📤 Copying backup to remote server..."
scp ${BACKUP_FILE} ${REMOTE_HOST}:${REMOTE_PATH}/

echo "📥 Restoring database on remote server..."

# Stop services on remote
ssh ${REMOTE_HOST} "cd ${REMOTE_PATH} && docker compose -f docker-compose.prod.yml stop backend frontend cloudflared"

sleep 3

# Drop and recreate database on remote
ssh ${REMOTE_HOST} "docker exec yt-transcript-db psql -U ${LOCAL_DB_USER} -d postgres -c 'DROP DATABASE IF EXISTS ${LOCAL_DB_NAME};'"
ssh ${REMOTE_HOST} "docker exec yt-transcript-db psql -U ${LOCAL_DB_USER} -d postgres -c 'CREATE DATABASE ${LOCAL_DB_NAME};'"

# Restore on remote
ssh ${REMOTE_HOST} "cat ${REMOTE_PATH}/${BACKUP_FILE} | docker exec -i yt-transcript-db psql -U ${LOCAL_DB_USER} -d ${LOCAL_DB_NAME}"

# Restart on remote
ssh ${REMOTE_HOST} "cd ${REMOTE_PATH} && docker compose -f docker-compose.prod.yml up -d"

# Cleanup on remote
ssh ${REMOTE_HOST} "rm ${REMOTE_PATH}/${BACKUP_FILE}"

echo "🧹 Cleaning up local backup..."
rm ${BACKUP_FILE}

echo "🎉 Migration complete!"