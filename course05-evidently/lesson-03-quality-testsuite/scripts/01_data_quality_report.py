"""
Bước 1 — DataQualityPreset: "dữ liệu có HỎNG không?" (khác với drift: "dữ liệu có ĐỔI không?")

reference = 500 dòng normal; current = 100 dòng normal rồi bị làm bẩn (inject_quality_issues).

Chạy: ../.venv/bin/python scripts/01_data_quality_report.py
"""
import warnings
from pathlib import Path

from evidently.metric_preset import DataQualityPreset
from evidently.report import Report

from data import inject_quality_issues, make_batch

warnings.filterwarnings("ignore")

reference = make_batch(500, "normal", seed=1)
current = inject_quality_issues(make_batch(100, "normal", seed=2))

report = Report(metrics=[DataQualityPreset()])
report.run(reference_data=reference, current_data=current)

out = Path(__file__).resolve().parent.parent / "reports"
out.mkdir(exist_ok=True)
report.save_html(str(out / "data_quality.html"))

metrics = report.as_dict()["metrics"]
print("DataQualityPreset bung ra các metric:")
for name in sorted({m["metric"] for m in metrics}):
    count = sum(m["metric"] == name for m in metrics)
    print(f"  - {name}" + (f"  (x{count}, mỗi cột một cái)" if count > 1 else ""))


def fmt(v):
    if v is None:
        return "-"
    return f"{v:.3f}" if isinstance(v, float) else str(v)


# --- Tóm tắt cấp dataset: đếm lỗi cấu trúc ---
summary = next(m["result"] for m in metrics if m["metric"] == "DatasetSummaryMetric")
ref_s, cur_s = summary.get("reference") or {}, summary.get("current") or {}
keys = ["number_of_rows", "number_of_missing_values", "number_of_duplicated_rows",
        "number_of_constant_columns", "number_of_almost_constant_columns", "number_of_empty_rows"]
print(f"\nDatasetSummaryMetric               {'reference':>10} {'current':>10}")
for k in keys:
    print(f"  {k:<34} {fmt(ref_s.get(k)):>10} {fmt(cur_s.get(k)):>10}")

# --- Thống kê từng cột: so reference vs current ---
print("\nColumnSummaryMetric (các cột bị làm bẩn)")
print(f"  {'cột':<10} {'tập':<9} {'missing%':>9} {'min':>8} {'mean':>8} {'max':>8} {'unique':>7}")
for m in metrics:
    if m["metric"] != "ColumnSummaryMetric":
        continue
    r = m["result"]
    if r["column_name"] not in ("alcohol", "pH", "sulphates"):
        continue
    for label, key in (("reference", "reference_characteristics"), ("current", "current_characteristics")):
        c = r.get(key) or {}
        print(f"  {r['column_name']:<10} {label:<9} {fmt(c.get('missing_percentage')):>9}"
              f" {fmt(c.get('min')):>8} {fmt(c.get('mean')):>8} {fmt(c.get('max')):>8}"
              f" {fmt(c.get('unique')):>7}")

print(f"""
Đã lưu {out / 'data_quality.html'}

Đọc kết quả:
  - Report chỉ ĐO và TRÌNH BÀY: missing, trùng, hằng số, min/max... Nó KHÔNG nói "đạt" hay "trượt".
  - alcohol thiếu 20%, pH có min = -1, sulphates unique = 1, số dòng trùng = 10.
  - tutorial07 có chạy DataQualityPreset nhưng không đọc kết quả → những lỗi này không lên
    Prometheus. Muốn tự động chặn/báo lỗi → cần điều kiện pass/fail = TestSuite (bước 2).
""")
