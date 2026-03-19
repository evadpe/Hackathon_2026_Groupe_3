FROM apache/airflow:2.10.5

COPY airflow/requirements.txt /tmp/requirements.txt
COPY --chmod=755 airflow/entrypoint.sh /entrypoint-custom.sh

RUN pip install --no-cache-dir -r /tmp/requirements.txt
