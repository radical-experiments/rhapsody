#!/usr/bin/env bash
set -e

IMAGE_PATH="redisai_latest.sif"
IMAGE_URI="docker://redislabs/redisai:latest"
TMPDIR_BASE="$HOME/RADICAL/ROSE"

prepare_env() {
    FULL_HOSTNAME=$(hostname -f 2>/dev/null || hostname)
    #echo "Preparing Apptainer environment for host: $FULL_HOSTNAME"

    TMPDIR_PATH="$TMPDIR_BASE/apptainer_tmp_${FULL_HOSTNAME}"
    CACHEDIR_PATH="$TMPDIR_BASE/apptainer_cache_${FULL_HOSTNAME}"

    mkdir -p "$TMPDIR_PATH" "$CACHEDIR_PATH"
    export APPTAINER_TMPDIR="$TMPDIR_PATH"
    export APPTAINER_CACHEDIR="$CACHEDIR_PATH"
}

run_redisai() {
    #echo "Starting RedisAI..."

    # Determine hostname
    FULL_HOSTNAME=$(hostname -f 2>/dev/null || hostname)
    DATA_DIR="/tmp/redis_data/${FULL_HOSTNAME}"

    # Create per-host redis directory
    mkdir -p "$DATA_DIR"

    #echo "Using data directory: $DATA_DIR"

    # Start RedisAI with per-host bind mount
    apptainer exec --cleanenv --bind "${DATA_DIR}:/data" "$IMAGE_PATH" \
        redis-server --loadmodule /usr/lib/redis/modules/redisai.so \
                     --port 6379 --dir /data --daemonize yes

    #echo "Waiting for RedisAI to respond..."

    # Use FULL_HOSTNAME consistently
    until apptainer exec "$IMAGE_PATH" redis-cli -h "$FULL_HOSTNAME" -p 6379 ping 2>/dev/null | grep -q "PONG"; do
        sleep 1
    done

    #echo "RedisAI is up and responding to PING."
    echo "${FULL_HOSTNAME}:6379"
}


shutdown_redisai() {
    echo "Shutting down RedisAI..."
    if apptainer exec "$IMAGE_PATH" redis-cli -h localhost -p 6379 shutdown >/dev/null 2>&1; then
        echo "RedisAI has been shut down."
    else
        echo "Could not connect to RedisAI — it may already be stopped."
    fi
}

# --- Main logic ---
if [ $# -ne 1 ]; then
    echo "Error: You must specify exactly one argument."
    echo "Usage: $0 {prepare_and_run|run|shutdown}"
    exit 1
fi

case "$1" in
  prepare_and_run)
    prepare_env
    run_redisai
    ;;
  run)
    if [ ! -f "$IMAGE_PATH" ]; then
        echo "Image '$IMAGE_PATH' not found. Run './redisai_apptainer.sh prepare_and_run' first."
        exit 1
    fi
    run_redisai
    ;;
  shutdown)
    shutdown_redisai
    ;;
  *)
    echo "Unknown argument: '$1'"
    echo "Usage: $0 {prepare_and_run|run|shutdown}"
    exit 1
    ;;
esac
