"""
Bước 2 — Đọc as_dict() đúng cách, rồi chạy lại NGUYÊN VĂN đoạn parse của tutorial07.

Chạy: ../.venv/bin/python scripts/02_parse_as_dict.py
"""
import warnings

from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

from data import make_batch

warnings.filterwarnings("ignore")

reference = make_batch(500, "normal", seed=1)
current = make_batch(100, "moderate_drift", seed=2)

report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=reference, current_data=current)
report_dict = report.as_dict()

# Tìm metric theo TÊN thay vì theo vị trí (thứ tự có thể đổi giữa các phiên bản)
by_name = {m["metric"]: m["result"] for m in report_dict["metrics"]}

# --- Cấp dataset ---
ds = by_name["DatasetDriftMetric"]
print("CẤP DATASET (DatasetDriftMetric)")
print(f"  số cột={ds['number_of_columns']}  số cột drift={ds['number_of_drifted_columns']}"
      f"  share={ds['share_of_drifted_columns']:.3f}")
print(f"  drift_share (ngưỡng)={ds['drift_share']}  → dataset_drift={ds['dataset_drift']}")

# --- Cấp cột ---
table = by_name["DataDriftTable"]
print("\nCẤP CỘT (DataDriftTable.drift_by_columns)")
print(f"  {'cột':<22} {'kiểm định':<24} {'ngưỡng':>6} {'drift_score':>12} {'drift':>6}")
for col, info in table["drift_by_columns"].items():
    # drift_score: với KS là p-value (nhỏ = drift); với Wasserstein là khoảng cách (lớn = drift)
    print(f"  {col:<22} {info['stattest_name']:<24} {info['stattest_threshold']:>6}"
          f" {info['drift_score']:>12.4g} {str(info['drift_detected']):>6}")

# --- Đoạn parse của tutorial07/evidently/main.py dòng 485–505 (chép nguyên logic) ---
drift_detected = False
drifted_features = []
drift_scores = {}
for metric in report_dict.get("metrics", []):
    if metric.get("metric") == "DatasetDriftMetric":
        result = metric.get("result", {})
        drift_detected = result.get("dataset_drift", False)
        drift_score = result.get("share_of_drifted_columns", 0)
        drift_by_columns = result.get("drift_by_columns", {})
        for feature, drift_info in drift_by_columns.items():
            drift_scores[feature] = drift_info.get("drift_score", 0)
            if drift_info.get("drift_detected", False):
                drifted_features.append(feature)
            # (tutorial07 set gauge FEATURE_DRIFT ở đây)

print("\nKẾT QUẢ THEO CODE TUTORIAL07")
print(f"  drift_detected   = {drift_detected}")
print(f"  drift_score      = {drift_score:.3f}")
print(f"  drifted_features = {drifted_features}")
print(f"  drift_scores     = {drift_scores}")

print("""
Đọc kết quả:
  - Cấp dataset của tutorial07 đúng (dataset_drift, share_of_drifted_columns).
  - drifted_features / drift_scores RỖNG dù bảng cột ở trên có cột drift: code tìm
    `drift_by_columns` trong DatasetDriftMetric, nhưng khóa đó nằm ở DataDriftTable.
    .get(..., {}) nuốt lỗi im lặng → vòng for không chạy → gauge FEATURE_DRIFT không bao giờ
    được set, drifted_count luôn 0. Sửa: đọc drift_by_columns từ metric "DataDriftTable".
""")
