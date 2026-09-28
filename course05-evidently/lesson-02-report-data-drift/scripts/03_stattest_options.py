"""
Bước 3 — Điều khiển Evidently: cỡ reference, ép kiểm định, ngưỡng, drift_share, kiểu cột.

Chạy: ../.venv/bin/python scripts/03_stattest_options.py
"""
import warnings

import numpy as np
from evidently.metric_preset import DataDriftPreset
from evidently.pipeline.column_mapping import ColumnMapping
from evidently.report import Report

from data import make_batch

warnings.filterwarnings("ignore")

ref_500 = make_batch(500, "normal", seed=1)
ref_2000 = make_batch(2000, "normal", seed=1)
cur_normal = make_batch(100, "normal", seed=3)
cur_slight = make_batch(100, "slight_drift", seed=4)


def run(label, preset, reference, current, column_mapping=None):
    report = Report(metrics=[preset])
    report.run(reference_data=reference, current_data=current, column_mapping=column_mapping)
    by_name = {m["metric"]: m["result"] for m in report.as_dict()["metrics"]}
    ds, cols = by_name["DatasetDriftMetric"], by_name["DataDriftTable"]["drift_by_columns"]
    tests = sorted({c["stattest_name"] for c in cols.values()})
    drifted = [c for c, info in cols.items() if info["drift_detected"]]
    print(f"\n=== {label} ===")
    print(f"  kiểm định: {tests}")
    print(f"  drift {ds['number_of_drifted_columns']}/{ds['number_of_columns']}"
          f"  share={ds['share_of_drifted_columns']:.2f}  ngưỡng share={ds['drift_share']}"
          f"  → dataset_drift={ds['dataset_drift']}")
    print(f"  cột drift: {drifted}")
    return cols


# A. Mặc định, reference 500 dòng → KS (p-value) cho mọi cột số
run("A. mặc định, ref=500, current=slight_drift", DataDriftPreset(), ref_500, cur_slight)

# B. Chỉ đổi cỡ reference lên 2000 → Evidently TỰ đổi sang Wasserstein normed
run("B. mặc định, ref=2000, current=slight_drift", DataDriftPreset(), ref_2000, cur_slight)

# C. Ép một kiểm định cho mọi cột + đổi ngưỡng.
#    Tên hay dùng: "ks", "wasserstein", "psi", "jensenshannon", "chisquare", "z", "kl_div".
#    PSI (Population Stability Index) quen thuộc trong ngân hàng: drift khi >= ngưỡng.
run("C. stattest='psi', ngưỡng 0.2", DataDriftPreset(stattest="psi", stattest_threshold=0.2),
    ref_500, cur_slight)

# D. Hạ drift_share: chỉ cần 30% cột drift là coi cả dataset drift (mặc định 0.5)
run("D. drift_share=0.3", DataDriftPreset(drift_share=0.3), ref_500, cur_slight)

# E. Kiểm định riêng cho từng cột (các cột còn lại vẫn theo mặc định)
run("E. per_column_stattest: pH dùng wasserstein",
    DataDriftPreset(per_column_stattest={"pH": "wasserstein"},
                    per_column_stattest_threshold={"pH": 0.2}),
    ref_500, cur_slight)

# F. Báo động giả: current KHÔNG drift nhưng 11 phép KS, mỗi phép có 5% xác suất báo nhầm
#    → gần như lúc nào cũng có 0–2 cột "drift". Nhờ ngưỡng drift_share mà dataset vẫn False.
run("F. current=normal (không drift thật)", DataDriftPreset(), ref_500, cur_normal)

# G. Kiểu cột: Evidently tự đoán số hay phân loại. Cột số nguyên ít giá trị (quality 3–8)
#    hoặc chuỗi (region) → nên khai báo rõ bằng ColumnMapping để không đoán sai.
rng = np.random.default_rng(5)
ref_g, cur_g = ref_500.copy(), cur_slight.copy()
ref_g["region"] = rng.choice(["north", "south"], size=len(ref_g), p=[0.5, 0.5])
cur_g["region"] = rng.choice(["north", "south"], size=len(cur_g), p=[0.8, 0.2])
ref_g["quality"] = rng.integers(3, 9, size=len(ref_g))
cur_g["quality"] = rng.integers(3, 9, size=len(cur_g))
mapping = ColumnMapping(
    numerical_features=[c for c in ref_500.columns],
    categorical_features=["region", "quality"],
)
cols = run("G. ColumnMapping: region, quality là phân loại", DataDriftPreset(), ref_g, cur_g, mapping)
for c in ("region", "quality"):
    print(f"  {c:<8} kiểu={cols[c]['column_type']}  kiểm định={cols[c]['stattest_name']}"
          f"  drift_score={cols[c]['drift_score']:.4g}")

print("""
Đọc kết quả:
  - A vs B: cùng current, chỉ đổi cỡ reference mà tên kiểm định và ý nghĩa drift_score đổi theo.
  - C, E: ép kiểm định/ngưỡng cho toàn bộ hoặc từng cột.
  - D: drift_share quyết định khi nào "cả dataset drift" — một con số chính sách, không phải thống kê.
  - F: 11 phép kiểm định cùng lúc → thỉnh thoảng có cột drift giả; đừng alert theo 1 cột lẻ.
  - G: region 2 giá trị + reference <= 1000 → Z-test; quality khai báo phân loại → chi-square.
""")
