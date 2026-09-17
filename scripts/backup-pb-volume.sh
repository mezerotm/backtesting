#!/bin/bash
set -euo pipefail

# Nightly PocketBase volume backup
# Backs up the finance-dashboard_pb_data Docker volume to /home/mezerotm/pb-backups/
# with rolling 7-day retention.

VOLUME_NAME="finance-dashboard_pb_data"
BACKUP_DIR="/home/mezerotm/pb-backups"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/finance-pb_data_${TIMESTAMP}.tar.gz"

echo "[backup-pb] Starting backup of volume $VOLUME_NAME ..."

# Mount volume read-only in alpine container, tar the data directory
docker run --rm -v ${VOLUME_NAME}:/pb_data:ro alpine tar cz -C /pb_data . > "$BACKUP_FILE"

BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null)
echo "[backup-pb] Backup written: $BACKUP_FILE ($BACKUP_SIZE bytes)"

# Rolling cleanup — remove backups older than RETENTION_DAYS
find "$BACKUP_DIR" -name 'finance-pb_data_*.tar.gz' -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

echo "[backup-pb] Done. Backups retained: $(ls "$BACKUP_DIR"/finance-pb_data_*.tar.gz 2>/dev/null | wc -l)"