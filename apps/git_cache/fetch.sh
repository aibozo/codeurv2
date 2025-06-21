#!/bin/sh
set -e

# Git cache sidecar script that maintains a bare mirror of the repository
# This allows multiple pods to share the same git repository cache

repo="$REPO_URL"
if [ -z "$repo" ]; then
    echo "[git-cache] ERROR: REPO_URL environment variable not set"
    exit 1
fi

# Create a deterministic directory name based on repo URL
mirror="/git-cache/$(echo "$repo" | sha1sum | cut -c1-20).git"

# Export metrics if port is configured
if [ -n "$METRICS_PORT" ]; then
    # Start simple HTTP server for metrics in background
    (
        while true; do
            if [ -d "$mirror" ]; then
                size=$(du -sb "$mirror" 2>/dev/null | cut -f1 || echo 0)
                printf "HTTP/1.1 200 OK\n\n# HELP git_cache_bytes Size of git cache in bytes\n# TYPE git_cache_bytes gauge\ngit_cache_bytes{repo=\"$(basename $repo .git)\"} $size\n" | nc -l -p ${METRICS_PORT:-9901} -q 1
            else
                printf "HTTP/1.1 200 OK\n\n# Git cache not yet initialized\n" | nc -l -p ${METRICS_PORT:-9901} -q 1
            fi
        done
    ) &
fi

# Initial clone or update
if [ ! -d "$mirror" ]; then
    echo "[git-cache] Mirroring $repo to $mirror..."
    start_time=$(date +%s)
    
    # Clone with retry logic
    retries=3
    while [ $retries -gt 0 ]; do
        if git clone --mirror "$repo" "$mirror"; then
            break
        fi
        retries=$((retries - 1))
        echo "[git-cache] Clone failed, retries left: $retries"
        sleep 5
    done
    
    if [ $retries -eq 0 ]; then
        echo "[git-cache] ERROR: Failed to clone repository after multiple attempts"
        exit 1
    fi
    
    end_time=$(date +%s)
    echo "[git-cache] Initial mirror completed in $((end_time - start_time)) seconds"
else
    echo "[git-cache] Updating existing mirror at $mirror..."
    start_time=$(date +%s)
    
    # Fetch updates with retry logic
    retries=3
    while [ $retries -gt 0 ]; do
        if git -C "$mirror" remote update --prune; then
            break
        fi
        retries=$((retries - 1))
        echo "[git-cache] Update failed, retries left: $retries"
        sleep 5
    done
    
    if [ $retries -eq 0 ]; then
        echo "[git-cache] ERROR: Failed to update repository after multiple attempts"
        exit 1
    fi
    
    end_time=$(date +%s)
    echo "[git-cache] Mirror updated in $((end_time - start_time)) seconds"
fi

# Write reference path for other containers
echo "$mirror" > /git-cache/reference-path

# Keep container running so volume stays mounted
echo "[git-cache] Cache ready at: $mirror"
echo "[git-cache] Keeping container alive..."

# Optionally start git daemon for HTTP access
if [ "$ENABLE_GIT_DAEMON" = "1" ]; then
    echo "[git-cache] Starting git daemon on port 9418..."
    git daemon --export-all --base-path=/git-cache --port=9418 &
fi

# Keep the container running
tail -f /dev/null