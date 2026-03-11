#!/bin/bash

# Safari-Shield Restore Script

set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <backup_date>"
    echo "Example: ./restore.sh 20240115_143022"
    exit 1
fi

BACKUP_DATE=$1
BACKUP_DIR="/backups"

echo "🚀 Starting restore from $BACKUP_DATE"

# Stop services
echo "🛑 Stopping services..."
docker-compose down

# Restore PostgreSQL
echo "📦 Restoring PostgreSQL..."
gunzip -c $BACKUP_DIR/postgres_$BACKUP_DATE.sql.gz | docker exec -i safari-shield-postgres psql -U safari fraud_db

# Restore Redis
echo "📦 Restoring Redis..."
docker cp $BACKUP_DIR/redis_$BACKUP_DATE.rdb safari-shield-redis:/data/dump.rdb
docker exec safari-shield-redis redis-cli CONFIG SET dir /data
docker exec safari-shield-redis redis-cli CONFIG SET dbfilename dump.rdb
docker exec safari-shield-redis redis-cli DEBUG RELOAD

# Restore models
echo "📦 Restoring models..."
tar -xzf $BACKUP_DIR/models_$BACKUP_DATE.tar.gz -C /app/models

# Rest