"""
BÀI 09 — Tự tay nói giao thức StatsD để hiểu Airflow gửi gì và mapping biến nó thành gì.

  python3 scripts/statsd_lab.py send     bắn vài dòng StatsD giả (dag_id = fake_dag) vào UDP 29125
  python3 scripts/statsd_lab.py show     đọc http://127.0.0.1:29102/metrics, in metric airflow_*
  python3 scripts/statsd_lab.py show --grep fake_dag

Chỉ dùng thư viện chuẩn, chạy bằng python3 trên máy (không cần venv).
"""
import argparse
import socket
import time
import urllib.request

UDP_ADDR = ("127.0.0.1", 29125)
METRICS_URL = "http://127.0.0.1:29102/metrics"

# Một dòng StatsD = "<tên>:<giá trị>|<loại>"  (c = counter, g = gauge, ms = timer mili-giây)
LINES = [
    # Khớp mapping "airflow.ti.finish.*.*.*" → airflow_task_finish_total{dag_id,task_id,state}
    "airflow.ti.finish.fake_dag.fake_task.failed:1|c",
    "airflow.ti.finish.fake_dag.fake_task.success:1|c",
    # Timer 1500 ms → exporter đổi thành 1.5 GIÂY, cộng vào _sum, _count tăng 1
    "airflow.dagrun.duration.success.fake_dag:1500|ms",
    # KHÔNG có mapping → vẫn được xuất, tên = thay "." bằng "_", không có label
    "airflow.fake_unmapped.fake_dag.value:42|g",
]


def send() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # UDP: gửi đi, không có phản hồi
    for line in LINES:
        sock.sendto(line.encode(), UDP_ADDR)
        print("gửi:", line)
    sock.close()
    time.sleep(0.5)
    print("\nGiờ chạy:  python3 scripts/statsd_lab.py show --grep fake")


def show(grep: str) -> None:
    body = urllib.request.urlopen(METRICS_URL, timeout=5).read().decode()
    shown = 0
    for line in body.splitlines():
        # Bỏ dòng "# HELP" / "# TYPE" cho gọn, trừ khi đang lọc (để thấy loại metric)
        if not line.startswith(("airflow_", "# TYPE airflow_")):
            continue
        if grep and grep not in line:
            continue
        if line.startswith("# TYPE") and not grep:
            continue
        print(line)
        shown += 1
    print(f"\n({shown} dòng)")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("send")
    p_show = sub.add_parser("show")
    p_show.add_argument("--grep", default="", help="chỉ in dòng chứa chuỗi này")
    args = parser.parse_args()
    if args.cmd == "send":
        send()
    else:
        show(args.grep)


if __name__ == "__main__":
    main()
