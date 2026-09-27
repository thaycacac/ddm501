ARG AIRFLOW_VERSION=2.10.5
FROM apache/airflow:${AIRFLOW_VERSION}-python3.10

ARG AIRFLOW_VERSION

COPY requirements.txt /requirements.txt

# Pin apache-airflow in the same resolve so extra packages cannot upgrade/downgrade Airflow itself
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements.txt

COPY --chown=airflow:root init_airflow.sh /opt/airflow/init_airflow.sh
