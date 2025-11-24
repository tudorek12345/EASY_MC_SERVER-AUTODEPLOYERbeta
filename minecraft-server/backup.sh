#!/bin/bash
SRC_DIR="/opt/minecraft/server"
BACKUP_DIR="/opt/minecraft/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
mkdir -p "$BACKUP_DIR"
tar --exclude="backups" --exclude="plugins/dynmap/web/tiles" -czf "$BACKUP_DIR/server_$TIMESTAMP.tar.gz" "$SRC_DIR"
find "$BACKUP_DIR" -type f -mtime +7 -delete
echo "Backup complete: $BACKUP_DIR/server_$TIMESTAMP.tar.gz"
