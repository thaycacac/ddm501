"""
Bước 2 — Cỡ mẫu làm thay đổi kết luận của p-value, nhưng không làm thay đổi khoảng cách.

Dữ liệu tổng hợp: reference ~ N(0, 1), current ~ N(shift, 1), cùng cỡ mẫu n.
  shift = 0.05σ → lệch "vô hại", thực tế không ảnh hưởng mô hình
  shift = 0.30σ → lệch đáng kể

Chạy: ../.venv/bin/python scripts/02_sample_size.py
"""
import numpy as np
from scipy import stats

rng = np.random.default_rng(7)

# Evidently 0.4.x chọn kiểm định mặc định cho feature số theo cỡ REFERENCE:
#   <= 1000 dòng → KS (p-value, drift khi < 0.05)
#   >  1000 dòng → Wasserstein normed (khoảng cách, drift khi >= 0.1)
EVIDENTLY_SWITCH = 1000

print(f"{'n':>7} {'shift':>6} | {'KS p-value':>11} {'KS drift':>8} | {'Wass':>6} {'W drift':>7}"
      f" | Evidently chọn → kết luận")
print("-" * 82)

for shift in (0.05, 0.30):
    for n in (50, 200, 1000, 5000, 50000):
        ref = rng.normal(0.0, 1.0, n)
        cur = rng.normal(shift, 1.0, n)

        p = stats.ks_2samp(ref, cur).pvalue
        w = stats.wasserstein_distance(ref, cur) / ref.std()
        ks_drift = p < 0.05
        w_drift = w >= 0.1

        if n <= EVIDENTLY_SWITCH:
            chosen, verdict = "KS", ks_drift
        else:
            chosen, verdict = "Wasserstein", w_drift

        print(f"{n:>7} {shift:>6.2f} | {p:>11.3g} {str(ks_drift):>8} | {w:>6.3f} {str(w_drift):>7}"
              f" | {chosen:<11} → drift={verdict}")
    print("-" * 82)

print("""
Đọc kết quả:
  - Hàng shift=0.05: n càng lớn, KS p-value càng nhỏ → tới n=50000 KS báo "drift" cho một
    thay đổi vô hại. p-value đo "chắc chắn là có khác", KHÔNG đo "khác nhiều hay ít".
  - Wasserstein ổn định quanh độ lệch thật (0.05 / 0.30) khi n lớn; khi n nhỏ nó bị nhiễu
    đẩy lên (báo động giả) → vì vậy Evidently dùng KS cho mẫu nhỏ, Wasserstein cho mẫu lớn.
  - Hệ quả khi đọc số: cùng tên "drift_score" nhưng lúc là p-value (nhỏ = drift), lúc là
    khoảng cách (lớn = drift) — tùy kiểm định Evidently đã chọn.
""")
