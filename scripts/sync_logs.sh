#!/usr/bin/env bash
set -euo pipefail

source .env.sync

REMOTE_DIR="${REMOTE_PROJECT_DIR}/logs/"


mkdir -p "${LOCAL_LOG_DIR}"

rsync -av --progress \
  "${SERVER_USER}@${SERVER_HOST}:${REMOTE_DIR}" \
  "${LOCAL_LOG_DIR}"

echo "Log sync completed."
