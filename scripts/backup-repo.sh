#!/bin/bash
# Automated git backup for finance-dash repo
# Commits all changes and pushes to backup branch on GitHub

REPO_DIR="/home/mezerotm/workspaces/finance"
BRANCH="backup/finance-dash-main"
LOG_FILE="/home/mezerotm/finance-repo-backups/backup-git.log"

mkdir -p "$(dirname "$LOG_FILE")"

cd "$REPO_DIR" || { echo "[$(date)] ERROR: Could not cd to $REPO_DIR" >> "$LOG_FILE"; exit 1; }

# Get current date stamp
STAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Stage all changes (including new files)
git add -A 2>/dev/null

# Check if there's anything to commit
if git diff --cached --quiet; then
    echo "[$STAMP] No changes to commit" >> "$LOG_FILE"
    exit 0
fi

# Commit with timestamp
git commit -m "auto-backup $STAMP"

# Push to the backup branch (force to overwrite old backup state)
git push origin main:"$BRANCH" --force 2>> "$LOG_FILE"

echo "[$STAMP] Backup push complete" >> "$LOG_FILE"