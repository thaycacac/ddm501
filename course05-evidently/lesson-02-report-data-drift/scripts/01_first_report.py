"""
Bước 1 — Report đầu tiên: chạy DataDriftPreset, lưu HTML, xem cấu trúc as_dict().

reference = 500 dòng "normal", current = 100 dòng "moderate_drift" (giống tutorial07).

Chạy: ../.venv/bin/python scripts/01_first_report.py
"""
import json
import warnings
from pathlib import Path

from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

from data import make_batch

# evidently 0.4.26 + pandas 2.0 in rất nhiều FutureWarning, không liên quan bài học
warnings.filterwarnings("ignore")

reference = make_batch(500, "normal", seed=1)
current = make_batch(100, "moderate_drift", seed=2)

# Report = danh sách metric. Preset = "gói" metric soạn sẵn cho một việc.
# DataDriftPreset tự chọn kiểm định cho từng cột theo quy tắc bài 01 (reference <= 1000 → KS).
report = Report(metrics=[DataDriftPreset()])

# run() mới là lúc tính toán thật. Cả 2 DataFrame phải cùng tên cột.
report.run(reference_data=reference, current_data=current)

# 1) HTML: báo cáo tương tác để NGƯỜI xem (tutorial07 lưu vào /app/reports, phục vụ qua /reports)
out_dir = Path(__file__).resolve().parent.parent / "reports"
out_dir.mkdir(exist_ok=True)
html_path = out_dir / "drift_moderate.html"
report.save_html(str(html_path))
print(f"Đã lưu báo cáo HTML: {html_path}")

# 2) as_dict(): cùng kết quả nhưng dạng dict để CODE đọc (tutorial07 dùng cái này)
result = report.as_dict()
print(f"\nKhóa cấp cao nhất của as_dict(): {list(result)}")
print(f"Preset đã bung ra {len(result['metrics'])} metric:")
for m in result["metrics"]:
    # mỗi phần tử: {"metric": <tên class>, "result": {...}}
    print(f"  - {m['metric']:<20} các khóa trong result: {list(m['result'])}")

# In gọn phần kết quả cấp dataset để nhìn tận mắt
dataset_metric = result["metrics"][0]
print(f"\n{dataset_metric['metric']}.result =")
print(json.dumps(dataset_metric["result"], indent=2, ensure_ascii=False))

print("""
Đọc kết quả:
  - DataDriftPreset không phải 1 metric mà là NHIỀU metric: một cái tóm tắt cả dataset,
    một cái là bảng drift từng cột.
  - Xem kỹ khóa `drift_by_columns` nằm trong result của metric NÀO — bước 2 cần điều này.
  - Mở file HTML bằng trình duyệt: mỗi cột có tên kiểm định, drift_score, histogram 2 tập.
""")
