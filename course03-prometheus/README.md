# Khóa thực hành: Prometheus + Grafana → Tutorial 06 (`ddm501-t04-monitoring`)

Mục tiêu cuối: đọc và giải thích được **từng dòng** của `../tutorial06/ddm501-t04-monitoring`,
làm được 5 bài tập và trả lời 6 câu checklist trong README của nó.

Vì sao cần: MLflow trả lời "đã train gì, model nào đang dùng". Airflow trả lời "pipeline
chạy thế nào, lỗi thì sao". Prometheus + Grafana trả lời "service đang phục vụ **ngay lúc
này** ra sao": bao nhiêu request, bao nhiêu lỗi, chậm hay nhanh, version nào, và model có
còn trả lời giống như lúc deploy không.

## Ports

| Service | Port khóa học | Ghi chú |
|---------|---------------|---------|
| Script demo (bài 01–02) | 28001 | `start_http_server`, chạy trên máy |
| API FastAPI | 28000 | từ bài 03 |
| Prometheus | 29090 | từ bài 04. Không đụng MinIO 29000/29001 của mlflow-course |
| Grafana | 23000 | từ bài 08 |
| (tutorial06) | 18000 / 19090 / 13000 | bật cùng lúc với khóa được |

## Quy ước mỗi bài

- Thư mục `lesson-NN-<chủ-đề>/`, có `READ_WITH_ME.py` (lý thuyết + danh sách file + ánh xạ vào tutorial06).
- Lý thuyết nằm **ngay trong comment** của code, đọc code là đọc bài.
- venv dùng chung ở `prometheus-course/.venv`, cài từ `requirements.txt` (cùng pin với tutorial06).
- Bài 01–03 chạy Python trên máy. Từ bài 04: Docker Compose, `name: prometheus-course-NN`,
  container `prometheus-course-NN-<service>`.
- Chỉ học **happy case**, trừ khi làm hỏng là nội dung bài (drift, lỗi, cardinality).
- Mỗi bài chỉ được tạo khi bạn học xong bài trước; mỗi bước hướng dẫn trên chat.
- **Nhịp học nhanh** (từ bài 03): không có câu hỏi/bài làm. Mỗi `READ_WITH_ME.py` kết thúc
  bằng mục **TỔNG KẾT** cô đọng bài học.

## Cài đặt (một lần)

```bash
cd prometheus-course
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Roadmap

| Bài | Chủ đề | Ánh xạ vào tutorial06 | Status |
|-----|--------|------------------------|--------|
| 01 | `/metrics`, pull model, exposition format, Counter, label, time series, rate bằng tay | `/metrics` trong `app/main.py`, Counter trong `app/metrics.py` | Xong |
| 02 | Histogram (bucket, `_sum`, `_count`, percentile) và Gauge, info pattern | `LATENCY`, `MODEL_LOADED`, `MODEL_INFO` | Xong |
| 03 | Gắn metric vào FastAPI chấm điểm WDBC, lỗi theo `reason`, cửa sổ `deque`, traffic | `app/`, `scripts/traffic.py` | Xong |
| 04 | Prometheus server trong Docker: scrape, Targets, `up`, reload, healthcheck | `prometheus.yml`, `docker-compose.yml`, `Dockerfile` | Xong |
| 05 | PromQL: instant/range vector, `rate`, `increase`, `sum by`, tỉ lệ lỗi | panel 1–2, `HighErrorRate` | Xong |
| 06 | PromQL histogram: `histogram_quantile`, p50/p95/p99, sai số bucket | panel 3, `SlowPredictions` | Xong |
| 07 | Alerting rules: `for`, pending/firing, annotations, `promtool` | `alerts/model.yml` | Xong |
| 08 | Grafana: provisioning datasource + dashboard JSON | `monitoring/grafana/**` | Xong |
| 09 | Monitoring riêng cho ML: drift của dự đoán, baseline | panel 4, `MalignantShareShift`, bài tập 4 | Xong |
| **10** | Label cardinality: bẫy `sample_id`, đếm series | `T04_TRAP`, `count_series.py`, bài tập 5 | **Đang học** |
| Capstone T06 | Chạy stack, làm 5 bài tập + 6 câu checklist, giải thích từng dòng | toàn bộ `../tutorial06/ddm501-t04-monitoring` | Chưa tạo |
| Bonus | Recording rules + Alertmanager (tutorial06 không có) | — | Chưa tạo |

## Bài đang học

```bash
cd lesson-10-cardinality
python READ_WITH_ME.py
```
