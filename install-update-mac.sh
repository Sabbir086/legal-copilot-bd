#!/bin/bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/Documents/legal-copilot-bd"
BACKUP_ROOT="$HOME/Documents/legal-copilot-backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/legal-copilot-bd-$TIMESTAMP"

if [[ ! -f "$SOURCE_DIR/README.md" || ! -d "$SOURCE_DIR/backend/app" || ! -d "$SOURCE_DIR/frontend/src" ]]; then
  echo "ERROR: Run this script from the extracted Legal Copilot update package root."
  exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "ERROR: Existing project not found at: $TARGET_DIR"
  echo "No files were changed. Extract the update into Downloads and confirm the target folder."
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "ERROR: rsync is required (it is normally available on macOS)."
  exit 1
fi

mkdir -p "$BACKUP_ROOT"
echo "Creating full backup: $BACKUP_DIR"
ditto "$TARGET_DIR" "$BACKUP_DIR"

# Overlay source only. No --delete: existing user files and unrelated files are retained.
# Secrets, local data, environments, dependencies and generated build output are excluded.
rsync -a "$SOURCE_DIR/" "$TARGET_DIR/" \
  --exclude='.git/' \
  --exclude='.env' \
  --exclude='.env.local' \
  --exclude='*.env.local' \
  --exclude='.env.*.local' \
  --exclude='backend/.env' \
  --exclude='frontend/.env.local' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='node_modules/' \
  --exclude='.next/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='*.tsbuildinfo' \
  --exclude='backend/uploads/' \
  --exclude='backend/reports/'

# Ensure local data folders still exist after overlay.
mkdir -p "$TARGET_DIR/backend/uploads" "$TARGET_DIR/backend/reports"

echo
echo "Update complete."
echo "Project: $TARGET_DIR"
echo "Backup:  $BACKUP_DIR"
echo "Existing .env files, .venv, node_modules, .git, uploads and reports were preserved."
echo "Review README.md and docs/MILESTONES.md before the next development step."
