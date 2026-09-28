"""
Mọi metric của service, gom một chỗ (= tutorial06/app/metrics.py).

Khai báo ở module riêng vì mỗi metric chỉ được đăng ký MỘT lần trong REGISTRY.
Khai báo trong hàm/route sẽ bị gọi lại → lỗi "Duplicated timeseries in CollectorRegistry".
"""
import os

from prometheus_client import Counter, Gauge, Histogram

# Bẫy cardinality của bài 10 (= T04_TRAP của tutorial06). Mặc định TẮT.
# Bật → thêm label sample_id: mỗi bệnh nhân một time series mới, mãi mãi.
TRAP = os.getenv("T04_TRAP", "0") == "1"

# --------------------------------------------------------------- COUNTER
# Câu hỏi: "đã phục vụ bao nhiêu dự đoán, và ra kết quả gì?"
# outcome ∈ {benign, malignant}: 2 giá trị, do model quyết định → label an toàn.
# Đọc bằng rate() (bài 05): "bao nhiêu dự đoán/giây ngay lúc này".
PREDICTIONS = Counter(
    "wdbc_predictions_total",
    "Predictions served, by outcome.",
    ["outcome"] + (["sample_id"] if TRAP else []),
)

# Câu hỏi: "bao nhiêu request thất bại, vì sao?"
# Chỉ đếm request LỖI. Tỉ lệ lỗi = errors / (errors + predictions) — bài 05.
ERRORS = Counter(
    "wdbc_errors_total",
    "Requests that failed, by reason.",
    ["reason"],
)

# ------------------------------------------------------------- HISTOGRAM
# Câu hỏi: "có chậm không — cho CẢ những người chậm nhất?"
# Bucket 1 ms → 1 s: LogisticRegression chấm một mẫu mất ~1–3 ms. Bucket mặc định
# (5 ms → 10 s) sẽ dồn mọi request vào bucket đầu → percentile vô nghĩa (bài 02).
LATENCY = Histogram(
    "wdbc_prediction_latency_seconds",
    "Time spent producing one prediction.",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# ----------------------------------------------------------------- GAUGE
# Câu hỏi: "process đang chạy, nhưng có phục vụ được không?"
MODEL_LOADED = Gauge(
    "wdbc_model_loaded",
    "1 if a model is loaded and able to serve, 0 otherwise.",
)

# Câu hỏi: "version nào đang phục vụ?" — info pattern (bài 02).
MODEL_INFO = Gauge(
    "wdbc_model_info",
    "Always 1. The labels are the point.",
    ["version", "sklearn_version"],
)

# Câu hỏi: "model còn trả lời giống lúc deploy không?"
# Đi theo DỮ LIỆU chứ không theo traffic: latency và lỗi có thể hoàn toàn bình
# thường trong khi con số này lệch xa — kiểu hỏng chỉ service ML mới có (bài 09).
MALIGNANT_SHARE = Gauge(
    "wdbc_malignant_share",
    "Share of the last 200 predictions that came out malignant.",
)
