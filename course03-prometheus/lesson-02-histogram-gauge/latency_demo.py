"""
Hai hệ thống có cùng latency trung bình (~40 ms) nhưng trải nghiệm khác hẳn,
cộng thêm các Gauge để thấy "con số lên xuống được" khác Counter thế nào.

Chạy:   python latency_demo.py
Xem:    curl -s localhost:28001/metrics | grep demo_
Dừng:   Ctrl+C
"""
import random
import time

from prometheus_client import Gauge, Histogram, start_http_server

PORT = 28001
OBS_PER_TICK = 20   # số request giả lập mỗi hệ thống, mỗi 0,5 giây

# --------------------------------------------------------------- HISTOGRAM
# buckets = các giới hạn trên (le), đơn vị GIÂY (quy ước của Prometheus: luôn dùng
# đơn vị cơ bản — giây, byte — và ghi đơn vị vào tên: _seconds, _bytes).
# Thư viện tự thêm bucket "+Inf" ở cuối để hứng mọi giá trị vượt 1 s.
#
# Label "system" chỉ để đặt 2 hệ thống cạnh nhau cho dễ so sánh. Mỗi giá trị label
# nhân toàn bộ bộ bucket lên: 2 hệ thống × (8 bucket + Inf + _sum + _count) = 22 series.
LATENCY = Histogram(
    "demo_latency_seconds",
    "Thời gian xử lý một request.",
    ["system"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# ------------------------------------------------------------------- GAUGE
# Mức hiện tại, lên xuống tự do. Đọc thẳng giá trị là có nghĩa.
QUEUE_DEPTH = Gauge(
    "demo_queue_depth",
    "Số việc đang chờ trong hàng đợi.",
)

# Cờ 1/0. Tutorial06: wdbc_model_loaded — process vẫn trả lời nhưng không có model
# thì cờ này = 0, và alert ModelNotLoaded bắt được điều mà port check bỏ sót (bài 07).
MODEL_LOADED = Gauge(
    "demo_model_loaded",
    "1 nếu model đã load và phục vụ được, 0 nếu không.",
)

# Info pattern: giá trị luôn là 1, dữ liệu nằm trong label.
# Label ở đây an toàn vì chỉ có MỘT tổ hợp tại một thời điểm (version đang chạy).
MODEL_INFO = Gauge(
    "demo_model_info",
    "Luôn bằng 1. Label mới là thông tin.",
    ["version", "sklearn_version"],
)


def steady() -> float:
    # Ai cũng ~40 ms.
    return random.uniform(0.035, 0.045)


def spiky() -> float:
    # 90% rất nhanh (~10 ms), 10% rất chậm (~310 ms).
    # Trung bình: 0.9*0.010 + 0.1*0.310 = 0.040 s — bằng steady.
    # Phần chậm là 10% (> 5%) nên p95 chắc chắn rơi vào nhóm chậm. Nếu phần chậm
    # đúng 5%, p95 nằm ngay ranh giới hai nhóm và nhảy qua lại giữa các lần chạy.
    return random.uniform(0.008, 0.012) if random.random() < 0.90 else random.uniform(0.28, 0.34)


def main() -> None:
    start_http_server(PORT)
    print(f"/metrics đang mở tại http://127.0.0.1:{PORT}/metrics  (Ctrl+C để dừng)")

    MODEL_LOADED.set(1)
    MODEL_INFO.labels(version="1.0.0", sklearn_version="1.6.0").set(1)

    depth = 0
    while True:
        for _ in range(OBS_PER_TICK):
            # .observe(giá_trị) = "một request vừa mất ngần này giây".
            # Ở service thật, bạn đo bằng time.perf_counter() quanh đúng phần việc
            # cần đo (tutorial06 main.py dòng 77–80), hoặc dùng `with LATENCY.time():`.
            # Ở đây giả lập nên không cần chờ thật — chỉ ghi số.
            LATENCY.labels(system="steady").observe(steady())
            LATENCY.labels(system="spiky").observe(spiky())

        # Random walk: hàng đợi lúc dài lúc ngắn. Counter không làm được việc này.
        depth = max(0, depth + random.randint(-3, 3))
        QUEUE_DEPTH.set(depth)

        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nđã dừng")
