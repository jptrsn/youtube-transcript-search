#!/bin/bash

# Script to migrate local database to remote server via SSH

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Configuration
LOCAL_DB_CONTAINER="${LOCAL_DB_CONTAINER:-youtube-transcripts-db}"
LOCAL_DB_NAME="${POSTGRES_DB:-youtube_transcripts}"
LOCAL_DB_USER="${POSTGRES_USER:-ytuser}"
REMOTE_HOST="${REMOTE_HOST}"
REMOTE_PATH="${REMOTE_PATH:-/opt/youtube-transcript-search}"
BACKUP_FILE="db_backup_$(date +%Y%m%d_%H%M%S).sql"

echo "🔄 Starting database migration process..."

# Step 1: Create local backup
echo "📦 Creating backup of local database..."
docker exec ${LOCAL_DB_CONTAINER} pg_dump -U ${LOCAL_DB_USER} ${LOCAL_DB_NAME} > ${BACKUP_FILE}

if [ $? -eq 0 ]; then
    echo "✅ Backup created: ${BACKUP_FILE} ($(du -h ${BACKUP_FILE} | cut -f1))"
else
    echo "❌ Failed to create backup"
    exit 1
fi

# Step 2: Copy backup to remote server
echo "📤 Copying backup to remote server..."
scp ${BACKUP_FILE} ${REMOTE_HOST}:${REMOTE_PATH}/

if [ $? -eq 0 ]; then
    echo "✅ Backup copied to remote server"
else
    echo "❌ Failed to copy backup"
    exit 1
fi

# Step 3: Restore on remote server (via docker exec, no exposed ports needed!)
echo "📥 Restoring database on remote server..."
ssh ${REMOTE_HOST} << EOF
    set -e
    cd ${REMOTE_PATH}

    echo "⏸️  Stopping backend to prevent connections..."
    docker compose -f docker-compose.prod.yml stop backend

    echo "🗑️  Dropping existing schema..."
    docker exec yt-transcript-db psql -U ${LOCAL_DB_USER} -d ${LOCAL_DB_NAME} -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

    echo "📥 Restoring database..."
    docker exec -i yt-transcript-db psql -U ${LOCAL_DB_USER} -d ${LOCAL_DB_NAME} < ${BACKUP_FILE}

    echo "▶️  Restarting backend..."
    docker compose -f docker-compose.prod.yml start backend

    echo "🧹 Cleaning up backup file..."
    rm ${BACKUP_FILE}

    echo "✅ Database restored successfully!"
EOF

if [ $? -eq 0 ]; then
    echo "✅ Remote database migration complete"
else
    echo "❌ Failed to restore database on remote server"
    exit 1
fi

# Step 4: Cleanup local backup
echo "🧹 Cleaning up local backup..."
rm ${BACKUP_FILE}

echo ""
echo "🎉 Migration complete!"
echo "Database successfully migrated from local to ${REMOTE_HOST}"