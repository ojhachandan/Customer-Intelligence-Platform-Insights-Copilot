#!/bin/sh
set -eu
# Lightweight container scheduler. Override CIP_SCHEDULE_SECONDS for development.
interval="${CIP_SCHEDULE_SECONDS:-86400}"
until cip init; do
  echo "database is not ready; retrying in 5 seconds" >&2
  sleep 5
done
while true; do
  cip ingest data/orders.csv
  cip features
  cip train
  cip recommend
  cip embed
  cip reports reports
  cip drift
  sleep "$interval"
done
