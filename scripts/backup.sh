#!/bin/bash

# Safari-Shield Backup Script

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

echo "🚀 Starting backup at $DATE"

# Backup PostgreSQL
echo "📦 Backing up PostgreSQL..."
docker exec safari-shield-postgres pg_dump -U safari fraud_db | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# Backup Redis
echo "📦 Backing up Redis..."
docker exec safari-shield-redis redis-cli SAVE
docker cp safari-shield-redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup models
echo "📦 Backing up models..."
tar -czf $BACKUP_DIR/models_$DATE.tar.gz -C /app/models .

# Backup configurations
echo "📦 Backing up configurations..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    -C /app deploy/ \
    -C /app .env \
    -C /app docker-compose.yml

# Upload to cloud storage (optional)
if [ ! -z "$AWS_BUCKET" ]; then
    echo "☁️ Uploading to S3..."
    aws s3 sync $BACKUP_DIR s3://$AWS_BUCKET/backups/$DATE/
fi

# Clean old backups
echo "🧹 Cleaning backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -type f -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -type f -name "*.rdb" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup completed successfully!"

# Send notification
curl -X POST -H "Content-Type: application/json" \
    -d "{\"text\":\"✅ Backup completed: $DATE (Size: $(du -sh $BACKUP_DIR | cut -f1))\"}" \
    $SLACK_WEBHOOK_URL