#!/usr/bin/env bash
set -euo pipefail

source .env.sync

REMOTE_DIR="${REMOTE_PROJECT_DIR}/data/raw/"

TODAY_UTC="$(date -u +%Y_%m_%d)"
TODAY_FILE="trades_${TODAY_UTC}.sqlite"

mkdir -p "${LOCAL_RAW_DIR}"

rsync -av --progress \
  --exclude "${TODAY_FILE}" \
  --exclude "*.sqlite-wal" \
  --exclude "*.sqlite-shm" \
  "${SERVER_USER}@${SERVER_HOST}:${REMOTE_DIR}" \
  "${LOCAL_RAW_DIR}"

echo "Raw data sync completed."
