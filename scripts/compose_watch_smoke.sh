#!/usr/bin/env bash
set -euo pipefail

required_services=(api worker beat redis)
log_file="${TMPDIR:-/tmp}/compose-watch.log"
pid_file="${TMPDIR:-/tmp}/compose-watch.pid"

cleanup() {
  if [ -f "$pid_file" ]; then
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi

  docker compose logs --tail=200 api worker beat redis || true
  docker compose down --remove-orphans --volumes || true
}

trap cleanup EXIT

rm -f "$log_file" "$pid_file"

docker compose up --build --watch >"$log_file" 2>&1 &
echo "$!" >"$pid_file"

for service in "${required_services[@]}"; do
  for attempt in $(seq 1 30); do
    if docker compose ps --format json "$service" | grep -q '"State":"running"'; then
      break
    fi

    if ! kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      echo "compose watch exited before $service reached running state" >&2
      cat "$log_file" >&2
      exit 1
    fi

    if [ "$attempt" -eq 30 ]; then
      echo "service did not reach running state: $service" >&2
      cat "$log_file" >&2
      exit 1
    fi

    sleep 2
  done
done

for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error http://127.0.0.1:8000/health >/dev/null; then
    echo "compose watch smoke check passed"
    exit 0
  fi

  if ! kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "compose watch exited before the API health check passed" >&2
    cat "$log_file" >&2
    exit 1
  fi

  if [ "$attempt" -eq 30 ]; then
    echo "API health check did not succeed before timeout" >&2
    cat "$log_file" >&2
    exit 1
  fi

  sleep 2
done

echo "API health check loop exited unexpectedly" >&2
exit 1
