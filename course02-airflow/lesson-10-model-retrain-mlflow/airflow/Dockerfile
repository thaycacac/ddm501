# BÀI 10 — Image Airflow cho DAG train (= tutorial07/airflow/Dockerfile).
# Nền là image khóa học (Airflow 2.8.4, python 3.11, pandas 2.1.4) + thư viện phía CLIENT của MLflow.
FROM airflow-course:2.8.4

USER airflow

# - Ghim apache-airflow==2.8.4 NGAY TRONG lệnh pip: pip phải giữ nguyên Airflow khi giải phụ thuộc,
#   không được nâng/hạ Airflow để chiều mlflow (mẹo của tutorial07).
# - mlflow-skinny: chỉ phần client (log, register, load). Bản đầy đủ `mlflow` kéo theo Flask,
#   SQLAlchemy, alembic... đụng version với chính Airflow.
# - mlflow-skinny CÙNG version với server (course01 bài 16: 2.19.0).
# - scikit-learn PHẢI trùng với image API: model pickle bằng bản nào thì load bằng bản đó.
# - boto3 (upload artifact lên MinIO) có sẵn trong image apache/airflow (provider amazon).
RUN pip install --no-cache-dir \
      "apache-airflow==2.8.4" \
      "mlflow-skinny==2.19.0" \
      "scikit-learn==1.5.2"
