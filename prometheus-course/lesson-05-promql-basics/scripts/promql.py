"""
Chạy một câu PromQL từ terminal qua HTTP API của Prometheus.

    python scripts/promql.py 'sum by (outcome) (rate(wdbc_predictions_total[1m]))'

Grafana (bài 08) cũng chỉ làm đúng việc này: gửi PromQL tới /api/v1/query
(hoặc /api/v1/query_range để lấy cả chuỗi điểm cho biểu đồ) rồi vẽ kết quả.
"""
import argparse

import httpx


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--url", default="http://127.0.0.1:29090")
    args = ap.parse_args()

    # /api/v1/query = instant query: đánh giá biểu thức TẠI MỘT thời điểm (mặc định: bây giờ).
    resp = httpx.get(f"{args.url}/api/v1/query", params={"query": args.query}, timeout=10.0)
    body = resp.json()
    if body["status"] != "success":
        print(f"lỗi: {body.get('errorType')}: {body.get('error')}")
        return

    data = body["data"]
    # resultType: vector (instant vector), matrix (range vector), scalar, string.
    print(f"resultType: {data['resultType']}   ({len(data['result'])} series)")
    if not data["result"]:
        # Rỗng không phải lỗi: không series nào khớp, hoặc bộ lọc (> 0.05) loại hết.
        print("  (rỗng)")
    for series in data["result"]:
        labels = {k: v for k, v in series["metric"].items()}
        name = labels.pop("__name__", "")
        label_str = ", ".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        if "value" in series:
            print(f"  {name}{{{label_str}}}  =  {float(series['value'][1]):.4f}")
        else:
            points = series["values"]
            print(f"  {name}{{{label_str}}}  →  {len(points)} điểm, "
                  f"đầu {points[0][1]}, cuối {points[-1][1]}")


if __name__ == "__main__":
    main()
