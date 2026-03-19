#!/usr/bin/env bash

set -euo pipefail

export AIRFLOW_HOME="${AIRFLOW_HOME:-/opt/airflow}"
export AIRFLOW_REPORTS_DIR="${AIRFLOW_REPORTS_DIR:-/opt/airflow/logs/reports}"

mkdir -p "${AIRFLOW_REPORTS_DIR}"

airflow db migrate

if airflow users create \
  --username admin \
  --firstname Step \
  --lastname Ahead \
  --role Admin \
  --email admin@localhost \
  --password admin; then
  echo "Airflow admin user created with fixed credentials."
else
  airflow users reset-password \
    --username admin \
    --password admin
  echo "Airflow admin password reset to fixed credentials."
fi

airflow scheduler &
exec airflow webserver
