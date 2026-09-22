#!/usr/bin/env bash
set -euo pipefail

# Clean up old raw trade SQLite files on the server.
#
# This script removes remote raw trade databases only when they are already
# present locally and older than one month. It is intended to keep the server
# storage small while the local raw-data directory acts as the current archive.
#
# Safety rules:
#   - Only files matching trades_YYYY_MM_DD.sqlite are considered.
#   - The file date must be older than the cutoff date.
#   - The same filename must exist in LOCAL_RAW_DIR.
#   - The local and remote file sizes must match.
#   - DRY_RUN defaults to true, so no files are deleted unless explicitly set.

source .env.sync

: "${SERVER_USER:?SERVER_USER is missing in .env.sync}"
: "${SERVER_HOST:?SERVER_HOST is missing in .env.sync}"
: "${REMOTE_PROJECT_DIR:?REMOTE_PROJECT_DIR is missing in .env.sync}"
: "${LOCAL_RAW_DIR:?LOCAL_RAW_DIR is missing in .env.sync}"

REMOTE_RAW_DIR="${REMOTE_PROJECT_DIR%/}/data/raw"
LOCAL_RAW_DIR="${LOCAL_RAW_DIR%/}"

# Default to dry-run mode to avoid accidental deletion.
DRY_RUN="${DRY_RUN:-true}"

# Files with dates before this value are considered older than one month.
CUTOFF_DATE="$(date -u -d "1 month ago" +%Y_%m_%d)"

REMOTE_RAW_DIR_QUOTED="$(printf "%q" "${REMOTE_RAW_DIR}")"

echo "Remote raw dir: ${REMOTE_RAW_DIR}"
echo "Local raw dir:  ${LOCAL_RAW_DIR}"
echo "Cutoff date:    ${CUTOFF_DATE}"
echo "Dry run:        ${DRY_RUN}"
echo

while IFS=$'\t' read -r filename remote_size; do
  # Only daily raw trade databases are allowed to enter the deletion logic.
  if [[ ! "${filename}" =~ ^trades_([0-9]{4}_[0-9]{2}_[0-9]{2})\.sqlite$ ]]; then
    echo "Skipping unexpected file: ${filename}"
    continue
  fi

  file_date="${BASH_REMATCH[1]}"

  # Lexicographic comparison works because dates use YYYY_MM_DD format.
  if [[ ! "${file_date}" < "${CUTOFF_DATE}" ]]; then
    echo "Keeping recent file: ${filename}"
    continue
  fi

  local_path="${LOCAL_RAW_DIR}/${filename}"

  # Never delete a remote file if the local archive copy is missing.
  if [[ ! -f "${local_path}" ]]; then
    echo "Keeping remote file because local copy is missing: ${filename}"
    continue
  fi

  local_size="$(wc -c < "${local_path}" | tr -d " ")"

  # Matching file size is a simple safety check before deleting remote data.
  if [[ "${local_size}" != "${remote_size}" ]]; then
    echo "Keeping remote file because size differs: ${filename} remote=${remote_size} local=${local_size}"
    continue
  fi

  remote_path="${REMOTE_RAW_DIR}/${filename}"
  remote_path_quoted="$(printf "%q" "${remote_path}")"

  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "DRY RUN would delete remote file: ${remote_path}"
  else
    # -n prevents this nested ssh call from consuming the while-loop input.
    ssh -n "${SERVER_USER}@${SERVER_HOST}" "rm -f -- ${remote_path_quoted}"
    echo "Deleted remote file: ${remote_path}"
  fi

done < <(
  ssh "${SERVER_USER}@${SERVER_HOST}" \
    "find ${REMOTE_RAW_DIR_QUOTED} -maxdepth 1 -type f -name 'trades_*.sqlite' -printf '%f\t%s\n'"
)

echo
echo "Remote raw cleanup completed."