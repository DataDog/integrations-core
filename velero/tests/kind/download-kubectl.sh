#!/bin/sh
set -eu

destination=$1
download=$(mktemp)
trap 'rm -f "$download"' 0
trap 'exit 1' HUP INT TERM

for attempt in 1 2 3; do
    echo "Downloading kubectl (attempt $attempt/3)..." >&2
    if timeout --kill-after=5s 60s wget --no-verbose --timeout=15 --tries=1 \
        --output-document="$download" https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl; then
        mv "$download" "$destination"
        exit 0
    else
        status=$?
    fi

    # Retry network errors and timeouts, including timeout's forced-kill exit status.
    case "$status" in
        4|124|137) ;;
        *)
            echo "kubectl download failed with non-retryable exit status $status." >&2
            exit "$status"
            ;;
    esac

    if [ "$attempt" -eq 3 ]; then
        echo "kubectl download failed after 3 attempts (exit status $status)." >&2
        exit "$status"
    fi

    delay=$((attempt * 2))
    echo "kubectl download failed (exit status $status); retrying in ${delay}s." >&2
    sleep "$delay"
done
