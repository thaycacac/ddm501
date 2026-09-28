# Khóa thực hành: Evidently → phần giám sát drift của Tutorial 07

Mục tiêu cuối: đọc và giải thích được **từng dòng** phần drift của `../tutorial07`:
`evidently/main.py` (service FastAPI chạy Evidently, xuất metric cho Prometheus),
`config/prometheus/evidently_alerts.yml` (alert drift), dashboard drift trong Grafana,
và biết con số `drift_score` trong đó **thực sự là gì**.

Vì sao cần: khóa Prometheus bài 09 mới đo drift kiểu "tỷ lệ dự đoán lệch khỏi baseline" — chỉ nhìn
**đầu ra**. Evidently so sánh **phân phối từng feature đầu vào** giữa dữ liệu tham chiếu
(reference) và dữ liệu gần đây (current) bằng kiểm định thống kê, rồi kết luận có drift hay không.

## Lộ trình tổng (3 khóa)

```
prometheus-course (xong) → alertmanager-course (xong) → evidently-course → airflow-course 05–10 → Capstone T07
```

## Cài môi trường (một lần)

`evidently==0.4.26` (bản tutorial07 dùng) đi kèm `numpy==1.24.3` — bản numpy này **không có wheel
cho Python 3.12**, nên khóa này dùng Python 3.10 (Homebrew đã có sẵn `/opt/homebrew/bin/python3.10`).

```bash
cd evidently-course
/opt/homebrew/bin/python3.10 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import evidently, numpy; print(evidently.__version__, numpy.__version__)"
# mong đợi: 0.4.26 1.24.3
```

## Ports

| Service | Port khóa học | Từ bài |
|---------|---------------|--------|
| Evidently service (FastAPI) | 28101 | 04 |
| Prometheus | 29090 | 05 |
| Alertmanager | 29093 | 05 |
| Grafana | 23000 | 05 |
| webhook-echo | 25001 | 05 |

Bài 01–03 chỉ chạy script trong venv, không cần Docker.

## Quy ước mỗi bài

- Thư mục `lesson-NN-<chủ-đề>/`, có `READ_WITH_ME.py` (lý thuyết + danh sách file + ánh xạ vào
  tutorial07), kết thúc bằng mục **TỔNG KẾT**. Không có câu hỏi/bài làm.
- Lý thuyết nằm ngay trong comment của code. **Mọi comment viết bằng tiếng Việt.**
- Script chạy bằng `../.venv/bin/python scripts/<tên>.py` từ thư mục bài.
- Dữ liệu: `sklearn.datasets.load_wine` (có sẵn trong scikit-learn, không cần tải) và bộ sinh dữ
  liệu mô phỏng lại `tutorial07/simulations/data_generator.py`.
- Mỗi bài chỉ được tạo khi bạn học xong bài trước; mỗi bước hướng dẫn trên chat.
- **Bạn tự chạy mọi lệnh.** Lỗi gì thì báo lại để cùng phân tích.

## Roadmap

| Bài | Chủ đề | Ánh xạ vào tutorial07 | Status |
|-----|--------|------------------------|--------|
| 01 | Thống kê của drift (tự tính bằng scipy): KS, Wasserstein, chi-square, Jensen-Shannon; p-value vs khoảng cách; ảnh hưởng cỡ mẫu | ý nghĩa `drift_score`, `simulations/data_generator.py` | Xong |
| 02 | Evidently `Report` + `DataDriftPreset`: `as_dict()`, `save_html()`, chọn stattest, ngưỡng, `ColumnMapping` | `evidently/main.py` hàm `perform_drift_analysis` | Xong |
| 03 | `DataQualityPreset` + `TestSuite` (pass/fail thay vì báo cáo) | `DataQualityPreset` trong `main.py` | Xong |
| 04 | Đưa Evidently thành service FastAPI: `/capture`, `/reference`, `/analyze`, gauge Prometheus | toàn bộ `evidently/main.py` (và tham số `threshold` bị bỏ qua) | Xong |
| 05 | Alert drift + Alertmanager + Grafana | `config/prometheus/evidently_alerts.yml`, dashboard drift | Xong |

## Trạng thái

Khóa đã xong. Học tiếp ở `../course02-airflow` (bài 05 → 10), rồi Capstone T07.
