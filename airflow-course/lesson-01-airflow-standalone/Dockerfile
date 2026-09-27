# BÀI 01 — image dùng cho cả khóa: Airflow gốc + 2 thư viện DAG cần.
# Giống hệt tutorial04/ddm501-t03-airflow/Dockerfile.

# Image chính thức đã có sẵn Airflow 2.8.4, user "airflow", AIRFLOW_HOME=/opt/airflow
FROM apache/airflow:2.8.4-python3.11

# pip install phải chạy bằng user airflow (image chính thức không cho cài bằng root)
USER airflow

ARG AIRFLOW_VERSION=2.8.4
ARG PYTHON_VERSION=3.11

# --constraint: file do Airflow công bố, ghim version MỌI thư viện đã test cùng
# Airflow 2.8.4. Không có nó, pip có thể kéo bản pandas/numpy mới làm hỏng Airflow.
# (Vì vậy pandas 2.1.4 chứ không phải 2.2.x như mlflow-course.)
RUN pip install --no-cache-dir \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
      "pandas==2.1.4" \
      "pyarrow==14.0.2"

# Không COPY dags/ vào image: dags/, data/, logs/ được bind mount lúc chạy
# → sửa DAG trên máy là Airflow thấy ngay, không cần build lại.
# Không có CMD: compose truyền "command: standalone" cho entrypoint của image.
