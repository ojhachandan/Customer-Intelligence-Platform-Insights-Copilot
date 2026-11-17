#!/bin/sh
set -e
# Robust container scheduler for The Qasar background analytical processing.
interval="${CIP_SCHEDULE_SECONDS:-86400}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Initializing database schema..."
until cip migrate; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database not ready; retrying in 5 seconds..." >&2
  sleep 5
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database ready. Ensuring seed demonstration data is available..."
cip ingest data/orders.csv || echo "[WARN] Seed order load bypassed"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting analytical pipeline loop (interval: ${interval}s)..."

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Running scheduled analytical refresh cycle..."

  # Run pipeline stages with fault isolation
  cip features || echo "[WARN] Features refresh reported an issue"
  cip train || echo "[WARN] Segmentation training reported an issue"
  cip recommend || echo "[WARN] Recommendation build reported an issue"
  cip embed || echo "[WARN] Embedding sync reported an issue"
  
  if [ -d "reports" ]; then
    cip reports reports || echo "[WARN] Report ingestion reported an issue"
  fi
  
  cip drift || echo "[WARN] Drift calculation reported an issue"

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cycle complete. Sleeping for ${interval}s..."
  sleep "$interval"
done
