# Khóa thực hành: Airflow → Tutorial 04 (`ddm501-t03-airflow`)

Mục tiêu cuối: đọc và giải thích được **từng dòng** của `../tutorial04/ddm501-t03-airflow`
(DAG `wdbc_pipeline`: ingest → validate → split → scale → report), rồi ghép Airflow
với stack MLflow đã dựng ở `../course01-mlflow`. Phần nâng cao (bài 06–10) phục vụ Tutorial 07.

Vì sao cần: MLflow trả lời "đã train gì, model nào đang dùng". Airflow trả lời
"ai chạy pipeline mỗi ngày, theo thứ tự nào, lỗi thì thử lại ra sao, chạy bù ngày
cũ thế nào, log từng bước ở đâu".

## Ports

| Service | Port khóa học | Ghi chú |
|---------|---------------|---------|
| Airflow UI | 28080 | 8080 của Lab 2, 18080 của tutorial04 → bật cùng lúc được. Đăng nhập `admin` / `admin` |
| (MLflow course) | 5001 / 25432 / 29000 | chỉ cần cho bài 10 |

## Quy ước mỗi bài

- Chạy bằng **Docker**. Image `airflow-course:2.8.4` build ở bài 01
  (`apache/airflow:2.8.4-python3.11` + pandas + pyarrow, cùng bản với tutorial04).
  Các bài sau chỉ ghi `image: airflow-course:2.8.4`, không build lại.
- Compose `name: airflow-course-NN`, container `airflow-course-NN-airflow`.
- Bind mount `./dags`, `./data`, `./logs` vào `/opt/airflow/...`.
- Mọi lệnh CLI chạy trong container: `docker compose exec airflow airflow <lệnh>`.
- File sinh ra khi chạy nằm trong `data/staging/` và `logs/` (git bỏ qua).
- Chỉ học **happy case**. Ngoại lệ: bài 05 cố ý làm hỏng dữ liệu, vì retry/fail là nội dung bài.
- Mỗi bài chỉ được tạo khi bạn học xong bài trước; mỗi bước hướng dẫn trên chat.

## Roadmap

| Bài | Chủ đề | Ánh xạ vào tutorial04 | Status |
|-----|--------|------------------------|--------|
| 01 | Airflow standalone trong Docker, UI, DAG hello, cấu hình `AIRFLOW__*` | `Dockerfile`, `docker-compose.yml` | Xong |
| 02 | Cấu trúc DAG + lịch chạy: `schedule`, `start_date`, `catchup`, logical date / `ds`, `dags test`, pause/unpause | `wdbc_pipeline.py` dòng 38–51 | Xong |
| 03 | TaskFlow `@task` + XCom: truyền dict, phụ thuộc tự động, `>>` khi truyền qua file, fan-in | dòng 54–69, 160–165 | Xong |
| 04 | Idempotency: thư mục theo `ds`, snapshot, parquet, chia bằng hash, `history.jsonl`, `backfill` | `run_dir`, `ingest`, `split`, `report` | Xong |
| 05 | Lỗi và retry: `retries` + backoff, `AirflowFailException`, quarantine + ngưỡng, log trong Grid | `validate`, `scripts/corrupt_extract.py` | Xong |
| Capstone T04 | (tùy chọn) Chạy stack tutorial04, làm 4 bài tập README, giải thích từng dòng | toàn bộ `../tutorial04/ddm501-t03-airflow` | Chưa tạo |

### Phần nâng cao (cho Tutorial 07)

| Bài | Chủ đề | Ánh xạ vào tutorial07 | Status |
|-----|--------|------------------------|--------|
| 06 | Rẽ nhánh và tham số: `@task.branch`, `EmptyOperator`, `trigger_rule`, `Param`, `dag_run.conf` | `airflow_dags/drift_monitoring.py` | Xong |
| 07 | DAG gọi DAG + callback: `TriggerDagRunOperator`, `on_failure_callback`, `max_active_runs`, util Telegram | `drift_monitoring.py` → `model_retrain.py`, `utils/telegram_alert.py` | Xong |
| 08 | Airflow kiểu production: LocalExecutor + Postgres, `airflow-init`, webserver/scheduler tách riêng, YAML anchor | `airflow/**`, service airflow-* trong `docker-compose.yml` | Xong |
| 09 | Metric của Airflow: StatsD → statsd-exporter → Prometheus, file mapping | `config/statsd_mapping.yml` | Xong |
| **10** | DAG train lại có quality gate: train → so sánh → register/promote alias trong MLflow → gọi `/model/reload` (thay Bonus cũ) | `airflow_dags/model_retrain.py`, nối `../course01-mlflow` bài 16 | **Đang học** |
| Capstone T07 | Chạy toàn bộ stack tutorial07, tái hiện bảng Evidence, sửa các alert hỏng, giải thích từng dòng | toàn bộ `../tutorial07` | Chưa tạo |

## Bài đang học

```bash
cd lesson-10-model-retrain-mlflow
python READ_WITH_ME.py
```
