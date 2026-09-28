"""
Service giả lập: mỗi giây xử lý vài "request", một phần bị lỗi.
Không có FastAPI, không có model — chỉ còn lại đúng phần metric để nhìn cho rõ.

Chạy:   python counter_demo.py
Xem:    curl localhost:28001/metrics
Dừng:   Ctrl+C
"""
import random
import time

from prometheus_client import Counter, start_http_server

PORT = 28001
RPS = 5            # số request giả lập mỗi giây
ERROR_RATE = 0.1   # 10% request lỗi

# ------------------------------------------------------------------ COUNTER
# Counter(tên, mô tả, [tên các label])
#
# - Tên: snake_case, có hậu tố _total. Nếu viết "demo_requests", thư viện tự
#   thêm "_total" khi xuất ra /metrics.
# - Mô tả: chính là dòng "# HELP" trên /metrics. Viết cho người trực sự cố đọc.
# - Label "status": chia một metric thành nhiều time series. Ở đây chỉ có
#   2 giá trị ("ok", "error") → đúng 2 series. Tập giá trị NHỎ và BIẾT TRƯỚC,
#   đó là điều kiện để label an toàn (bài 10).
#
# Tutorial06 làm y hệt: wdbc_predictions_total{outcome} và wdbc_errors_total{reason}.
REQUESTS = Counter(
    "demo_requests_total",
    "Số request đã xử lý, theo kết quả.",
    ["status"],
)

# Counter không label: chỉ một series duy nhất.
BYTES_SENT = Counter(
    "demo_response_bytes_total",
    "Tổng số byte đã trả về cho client.",
)


def handle_one_request() -> None:
    # .labels(status=...) chọn ra đúng time series cần tăng, rồi .inc() cộng 1.
    # Series chỉ xuất hiện trên /metrics từ lần đầu .labels(...) được gọi với giá
    # trị đó — trước lần lỗi đầu tiên, bạn sẽ không thấy dòng status="error".
    if random.random() < ERROR_RATE:
        REQUESTS.labels(status="error").inc()
    else:
        REQUESTS.labels(status="ok").inc()
        # .inc(n) cộng n. Số âm bị từ chối (ValueError): counter không bao giờ giảm.
        BYTES_SENT.inc(random.randint(200, 800))


def main() -> None:
    # start_http_server mở một HTTP server chạy ở thread nền, phục vụ /metrics.
    # Đây là toàn bộ "tích hợp" với Prometheus: mở một trang, rồi thôi.
    # Service không gửi gì đi đâu — Prometheus sẽ tự đến lấy (pull model).
    start_http_server(PORT)
    print(f"/metrics đang mở tại http://127.0.0.1:{PORT}/metrics  (Ctrl+C để dừng)")

    handled = 0
    while True:
        handle_one_request()
        handled += 1
        if handled % (RPS * 10) == 0:
            print(f"  đã xử lý {handled} request")
        time.sleep(1 / RPS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Process kết thúc → mọi counter nằm trong RAM mất theo.
        # Chạy lại sẽ bắt đầu từ 0: đó là "counter reset".
        print("\nđã dừng — counter trong RAM đã mất")
