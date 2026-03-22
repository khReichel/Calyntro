#!/bin/bash

# Ensure UID/GID are available for docker-compose
export HOST_UID=$(id -u)
export HOST_GID=$(id -g)

# Ensure volume directories exist and belong to the current user
ensure_volume_dir() {
    local dir="$1"

    if [ ! -d "$dir" ]; then
        echo "Creating volume directory: $dir"
        mkdir -p "$dir"
    fi

    # Fix ownership recursively
    local owner_uid
    owner_uid=$(stat -c %u "$dir")

    if [ "$owner_uid" != "$HOST_UID" ]; then
        echo "Fixing ownership for $dir"
        chown -R "$HOST_UID:$HOST_GID" "$dir"
    fi
}


# Configuration
CONFIG_FILE="config/config.yaml"

# 1. Attempt to get the actual bridge gateway IP
DETECTED_GATEWAY=$(docker network inspect bridge --format='{{(index .IPAM.Config 0).Gateway}}' 2>/dev/null)

# 2. Fallback logic: If detection fails, use the keyword 'host-gateway'
# (which works on Docker Desktop). If it succeeds, use the IP.
if [ -z "$DETECTED_GATEWAY" ]; then
    export DOCKER_GATEWAY="host-gateway"
else
    export DOCKER_GATEWAY="$DETECTED_GATEWAY"
fi

echo "--- Network Setup: Mapping host.docker.internal to $DOCKER_GATEWAY ---"

# --- Helper Functions ---

read_yaml_key() {
    local key="$1"
    grep -E "^[[:space:]]*$key:" "$CONFIG_FILE" \
        | sed -E 's/^[^:]+:[[:space:]]*"?([^"#]+)"?.*/\1/'
}


case "$1" in
  # 1. Start everything
  up)
      ensure_volume_dir "./data"
      ensure_volume_dir "./exports"
      ensure_volume_dir "./repo"
      ensure_volume_dir "./grafana"
      ensure_volume_dir "./grafana/data"
      ensure_volume_dir "./grafana/provisioning"
      ensure_volume_dir "./grafana/provisioning/dashboards"
      ensure_volume_dir "./grafana/provisioning/datasources"

    MODE="${2:-prod}"
    case "$MODE" in
      dev)
        echo "Starting development environment..."
        docker compose -f docker-compose.dev.yml up -d --build
        ;;
      prod)
        echo "Starting production environment..."
        docker compose -f docker-compose.yml up -d --build
        ;;
      *)
        echo "Starting production environment..."
        docker compose -f docker-compose.yml up -d --build
        ;;
    esac
    ;;

  # Shut down containers
  down)
    echo "Stopping and removing containers..."
    docker compose down
    echo "All services have been shut down."
    ;;

  # 2. Refresh: Atomic swap from staging to production
  refresh)
    echo "--- Refreshing RepoLens database from staging ---"
    ensure_volume_dir "./data"
    # Read values from YAML
    DB_PATH=$(read_yaml_key "db_path")
    DB_UPDATE_PATH=$(read_yaml_key "db_update_path")
    DB_BASENAME=$(read_yaml_key "db_basename")

    # Validate
    if [ -z "$DB_PATH" ] || [ -z "$DB_UPDATE_PATH" ] || [ -z "$DB_BASENAME" ]; then
        echo "Error: Could not read required keys from $CONFIG_FILE"
        echo "Required keys: db_path, db_update_path, db_basename"
        exit 1
    fi

    echo "DB_PATH: $DB_PATH"
    echo "DB_UPDATE_PATH: $DB_UPDATE_PATH"
    echo "DB_BASENAME: $DB_BASENAME"

    # Convert container paths to host paths
    HOST_DB_PATH=${DB_PATH/\/app\//./}
    HOST_UPDATE_PATH=${DB_UPDATE_PATH/\/app\//./}

    STAGING_ANALYSIS="${HOST_UPDATE_PATH}/${DB_BASENAME}.duckdb"
    STAGING_CONFIG="${HOST_UPDATE_PATH}/${DB_BASENAME}_config.duckdb"

    if [[ ! -f "$STAGING_ANALYSIS" ]] || [[ ! -f "$STAGING_CONFIG" ]]; then
        echo "Error: Staging database not found at '$HOST_UPDATE_PATH'"
        echo "Expected: $STAGING_ANALYSIS and $STAGING_CONFIG"
        exit 1
    fi

    echo "Stopping backend..."
    docker compose stop backend

    # Backup
    BACKUP_DIR="${HOST_DB_PATH}/backup_$(date +%Y%m%d_%H%M%S)"
    echo "Creating backup in $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    cp "${HOST_DB_PATH}/${DB_BASENAME}.duckdb" "$BACKUP_DIR/" 2>/dev/null || true
    cp "${HOST_DB_PATH}/${DB_BASENAME}_config.duckdb" "$BACKUP_DIR/" 2>/dev/null || true

    # Swap
    echo "Copying staging files to production..."
    cp "$STAGING_ANALYSIS" "${HOST_DB_PATH}/${DB_BASENAME}.duckdb"
    cp "$STAGING_CONFIG" "${HOST_DB_PATH}/${DB_BASENAME}_config.duckdb"

    echo "Starting backend..."
    docker compose up -d backend

    echo "--- Refresh completed ---"
    ;;

  # 3. Import: Run full import and analysis
  import)
      ensure_volume_dir "./data"
      ensure_volume_dir "./exports"
      ensure_volume_dir "./repo"
      REPO_DIR=""

      if [ -z "$2" ]; then
          REPO_DIR=$(read_yaml_key "repo_path")

          if [ -z "$REPO_DIR" ]; then
              echo "Error: Could not read 'repo_path' from $CONFIG_FILE"
              exit 1
          fi

          echo "Using repository path from config: $REPO_DIR"
      else
          REPO_DIR=$(realpath "$2")
      fi

      if [ ! -d "$REPO_DIR" ]; then
          echo "Error: Repository directory does not exist: $REPO_DIR"
          exit 1
      fi

    echo "Running import for repository at $REPO_DIR..."
    export REPO_PATH_HOST="$REPO_DIR"

    docker compose run --rm importer config --config-file /app/config/config.yaml
    docker compose run --rm importer analysis --config-file /app/config/config.yaml

    unset REPO_PATH_HOST
    echo "Import and analysis complete."
    ;;

  # 4. Maintenance Commands
  pull-latest)
    echo "Pulling latest images from GitHub..."
    docker login ghcr.io
    docker compose pull
    docker compose up -d
    echo "Update complete."
    ;;

  update)
    echo "Rebuilding and restarting containers..."
    docker compose up -d --build --remove-orphans
    echo "Update complete."
    ;;

  logs)
    echo "Streaming logs to ./logs/combined_$(date +%Y%m%d).log ..."
    mkdir -p ./logs
    docker compose logs -f -t > ./logs/combined_$(date +%Y%m%d).log 2>&1 &
    echo "Log streaming started in background."
    ;;

  debug-path)
    docker compose run --rm -e PYTHONPATH=/app/src importer python -c "import sys; import os; print('--- Python Search Path ---'); [print(p) for p in sys.path]; print('\n--- /app/src content ---'); os.system('ls -l /app/src')"
    ;;

  *)
    echo "Usage: ./manage.sh <command>"
    echo "Commands:"
    echo "  up [prod|dev]          - Start services (default: prod)"
    echo "  down                   - Stop and remove services"
    echo "  import [path]          - Run import/analysis (uses config path if omitted)"
    echo "  refresh                - Move staging DB to production"
    echo "  pull-latest            - Pull images from registry and restart"
    echo "  update                 - Rebuild and restart containers"
    echo "  logs                   - Stream logs to background file"
    echo "  debug-path             - Check container Python environment"
    exit 1
    ;;
esac
