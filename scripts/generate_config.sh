#!/bin/bash
# scripts/generate_config.sh
#
# Generates a draft Calyntro config.yaml by scanning a git repository.
# Runs generate_config.py inside the Calyntro backend image — no local
# Python dependencies required beyond Docker.
#
# Usage:
#   ./scripts/generate_config.sh <repo_path> [options]
#
# Options passed through to generate_config.py:
#   --branch BRANCH       Branch to scan          (default: auto-detected)
#   --since  YYYY-MM-DD   analysis_since date     (default: 2020-01-01)
#   --threshold FLOAT     Min commit share for a component (default: 0.02)
#   -o, --output PATH     Output file on the HOST  (default: stdout)
#
# Examples:
#   ./scripts/generate_config.sh /path/to/myrepo
#   ./scripts/generate_config.sh /path/to/myrepo --branch master --since 2022-01-01
#   ./scripts/generate_config.sh /path/to/myrepo -o config/config.yaml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE="ghcr.io/khreichel/calyntro-backend:latest"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <repo_path> [--branch BRANCH] [--since YYYY-MM-DD] [-o OUTPUT]"
    exit 1
fi

REPO_HOST="$(realpath "$1")"
shift

if [[ ! -d "$REPO_HOST/.git" ]]; then
    echo "Error: $REPO_HOST is not a git repository."
    exit 1
fi

# --- Parse -o / --output to remap host path to container path ---
CONTAINER_ARGS=()
OUTPUT_HOST=""
OUTPUT_CONTAINER=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--output)
            OUTPUT_HOST="$(realpath -m "$2")"
            OUTPUT_CONTAINER="/output/$(basename "$OUTPUT_HOST")"
            CONTAINER_ARGS+=("--output" "$OUTPUT_CONTAINER")
            shift 2
            ;;
        *)
            CONTAINER_ARGS+=("$1")
            shift
            ;;
    esac
done

# --- Build docker run command ---
DOCKER_ARGS=(
    --rm
    --pull=never
    -e GIT_CONFIG_COUNT=1
    -e GIT_CONFIG_KEY_0=safe.directory
    -e GIT_CONFIG_VALUE_0=/repo
    -v "$PROJECT_DIR/scripts/generate_config.py:/app/generate_config.py:ro"
    -v "$REPO_HOST:/repo:ro"
)

if [[ -n "$OUTPUT_HOST" ]]; then
    mkdir -p "$(dirname "$OUTPUT_HOST")"
    DOCKER_ARGS+=(-v "$(dirname "$OUTPUT_HOST"):/output")
fi

# Use local image if available, fall back to published image
if docker image inspect "calyntro-backend:latest" > /dev/null 2>&1; then
    IMAGE="calyntro-backend:latest"
fi

echo "Image: $IMAGE"
echo "Repo:  $REPO_HOST"

docker run "${DOCKER_ARGS[@]}" \
    --entrypoint python \
    "$IMAGE" \
    /app/generate_config.py /repo "${CONTAINER_ARGS[@]}"
