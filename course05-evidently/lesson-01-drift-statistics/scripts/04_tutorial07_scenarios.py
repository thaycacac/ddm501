"""
Bước 4 — Áp vào dữ liệu mô phỏng của tutorial07 và tính "dataset drift" bằng tay.

Mô phỏng lại đúng logic tutorial07/simulations/data_generator.py (11 feature wine quality):
  - mẫu bình thường: N(mean, std), cắt vào [min, max]
  - mẫu drift: MỖI MẪU chọn ngẫu nhiên `affected` feature, feature đó = mean × multiplier
    + nhiễu N(0, std × noise), cắt vào [min, max]

reference = 500 mẫu bình thường; current = 100 mẫu (= window_size mặc định của /analyze).
Sau đó làm y như Evidently với reference <= 1000 dòng: KS cho từng feature, rồi
  share_of_drifted_columns = số feature drift / tổng số feature
  dataset_drift            = share >= 0.5

Chạy: ../.venv/bin/python scripts/04_tutorial07_scenarios.py
"""
import numpy as np
from scipy import stats

# chép từ tutorial07/simulations/config.yaml: (min, max, mean, std)
FEATURES = {
    "fixed_acidity": (4.6, 15.9, 8.32, 1.74),
    "volatile_acidity": (0.12, 1.58, 0.53, 0.18),
    "citric_acid": (0.0, 1.0, 0.27, 0.19),
    "residual_sugar": (0.9, 15.5, 2.54, 1.41),
    "chlorides": (0.012, 0.611, 0.087, 0.047),
    "free_sulfur_dioxide": (1.0, 72.0, 15.87, 10.46),
    "total_sulfur_dioxide": (6.0, 289.0, 46.47, 32.90),
    "density": (0.99007, 1.00369, 0.9967, 0.0019),
    "pH": (2.74, 4.01, 3.31, 0.15),
    "sulphates": (0.33, 2.0, 0.66, 0.17),
    "alcohol": (8.4, 14.9, 10.42, 1.07),
}
NAMES = list(FEATURES)
# (multiplier, noise, số feature bị drift trong MỖI mẫu)
SCENARIOS = {
    "normal": None,
    "slight_drift": (1.2, 0.15, 2),
    "moderate_drift": (1.5, 0.2, 4),
    "severe_drift": (2.0, 0.3, 7),
    "sudden_shift": (2.5, 0.4, 10),
}

rng = np.random.default_rng(2024)


def normal_sample():
    return {f: np.clip(rng.normal(mean, std), lo, hi) for f, (lo, hi, mean, std) in FEATURES.items()}


def make_batch(n, scenario):
    rows = []
    for _ in range(n):
        row = normal_sample()
        if SCENARIOS[scenario]:
            mult, noise, k = SCENARIOS[scenario]
            for f in rng.choice(NAMES, size=k, replace=False):
                lo, hi, mean, std = FEATURES[f]
                row[f] = np.clip(mean * mult + rng.normal(0, std * noise), lo, hi)
        rows.append(row)
    return {f: np.array([r[f] for r in rows]) for f in NAMES}


reference = make_batch(500, "normal")

print(f"{'scenario':<15} | {'drift/11':>8} {'share':>6} {'dataset_drift':>13} | feature bị drift")
print("-" * 100)
detail = {}
for scenario in SCENARIOS:
    current = make_batch(100, scenario)
    pvalues = {f: stats.ks_2samp(reference[f], current[f]).pvalue for f in NAMES}
    drifted = [f for f, p in pvalues.items() if p < 0.05]
    share = len(drifted) / len(NAMES)
    detail[scenario] = pvalues
    print(f"{scenario:<15} | {len(drifted):>8} {share:>6.2f} {str(share >= 0.5):>13} | {', '.join(drifted)}")

print("\nChi tiết p-value từng feature (drift khi < 0.05):")
print(f"{'feature':<22}" + "".join(f"{s:>15}" for s in SCENARIOS))
for f in NAMES:
    print(f"{f:<22}" + "".join(f"{detail[s][f]:>15.3g}" for s in SCENARIOS))

print("""
Đọc kết quả:
  - Mỗi mẫu drift chỉ đụng k/11 feature → với một feature, current là HỖN HỢP: phần lớn mẫu
    bình thường + một phần mẫu lệch. slight_drift: mỗi feature chỉ ~2/11 ≈ 18% mẫu bị lệch.
  - "slight" không nhẹ như tên: mean × 1.2 của pH (3.31 → 3.97) là dịch ~4.4σ, còn citric_acid
    (0.27 → 0.32) chỉ ~0.3σ. Feature có mean lớn so với std thì nhân hệ số → dịch rất xa.
  - dataset_drift chỉ True khi >= 50% feature drift → kịch bản nhẹ có thể có vài feature
    drift mà toàn bộ dataset vẫn "không drift". Đó là số tutorial07 gửi lên Prometheus.
""")
