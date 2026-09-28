"""
Bước 1 — Feature SỐ: KS test và Wasserstein trên cột `alcohol` của bộ wine (178 dòng).

Chia ngẫu nhiên 178 dòng thành 2 nửa 89/89:
  reference = nửa 1 (coi như dữ liệu lúc train)
  current   = nửa 2, rồi dịch thêm 0σ / 0.5σ / 1σ để giả lập drift

Chạy: ../.venv/bin/python scripts/01_numeric_tests.py
"""
import numpy as np
from scipy import stats
from sklearn.datasets import load_wine

# seed cố định → mỗi lần chạy ra đúng cùng con số
rng = np.random.default_rng(42)

values = load_wine(as_frame=True).frame["alcohol"].to_numpy()
order = rng.permutation(len(values))
reference = values[order[:89]]
current_base = values[order[89:]]
sigma = reference.std()

# Ngưỡng mặc định của Evidently:
#   kiểm định trả p-value  → drift khi p-value < 0.05
#   kiểm định trả khoảng cách → drift khi khoảng cách >= 0.1
P_THRESHOLD = 0.05
DIST_THRESHOLD = 0.1


def ascii_hist(ref, cur, bins=12, width=30):
    """Vẽ 2 histogram cạnh nhau bằng ký tự, cùng một bộ bin để so được."""
    edges = np.linspace(min(ref.min(), cur.min()), max(ref.max(), cur.max()), bins + 1)
    ref_counts, _ = np.histogram(ref, edges)
    cur_counts, _ = np.histogram(cur, edges)
    top = max(ref_counts.max(), cur_counts.max())
    print(f"    {'bin':>11} | {'reference':<{width}} | current")
    for i in range(bins):
        r = "#" * round(ref_counts[i] / top * width)
        c = "#" * round(cur_counts[i] / top * width)
        print(f"    {edges[i]:5.2f}-{edges[i + 1]:5.2f} | {r:<{width}} | {c}")


def compare(label, ref, cur):
    # KS (Kolmogorov–Smirnov 2 mẫu):
    #   statistic D = khoảng cách LỚN NHẤT giữa 2 hàm phân phối tích lũy (ECDF), trong [0, 1]
    #   p-value     = xác suất thấy D lớn cỡ này NẾU 2 mẫu thật ra cùng một phân phối
    #   → p-value NHỎ = khó tin là cùng phân phối = DRIFT
    ks = stats.ks_2samp(ref, cur)

    # Wasserstein (earth mover's distance): "công" ít nhất để dời đống cát histogram này
    # thành đống kia; đơn vị = đơn vị của feature (ở đây: độ cồn %).
    # Evidently chia cho std của reference ("wasserstein normed") để mọi feature cùng thang:
    #   0.1 nghĩa là trung bình phải dời 0.1σ
    #   → khoảng cách LỚN = DRIFT (ngược chiều với p-value!)
    wd = stats.wasserstein_distance(ref, cur) / np.std(ref)

    print(f"\n=== {label} ===")
    print(f"  mean reference={ref.mean():.3f}  mean current={cur.mean():.3f}  (σ_ref={sigma:.3f})")
    ascii_hist(ref, cur)
    print(f"  KS          D={ks.statistic:.3f}  p-value={ks.pvalue:.4g}"
          f"  → drift={ks.pvalue < P_THRESHOLD}  (drift khi p < {P_THRESHOLD})")
    print(f"  Wasserstein normed={wd:.3f}"
          f"  → drift={wd >= DIST_THRESHOLD}  (drift khi >= {DIST_THRESHOLD})")


compare("A. current = nửa còn lại, KHÔNG dịch (không drift thật)", reference, current_base)
compare("B. current dịch +0.5σ", reference, current_base + 0.5 * sigma)
compare("C. current dịch +1.0σ", reference, current_base + 1.0 * sigma)

print("""
Đọc kết quả:
  - A: KS p-value lớn → không drift. Wasserstein KHÔNG bằng 0 dù không drift: 89 mẫu thì hai
       nửa tự nhiên đã khác nhau chút → có thể vượt 0.1 (báo động giả). Đây là lý do
       Evidently chỉ dùng Wasserstein khi reference > 1000 dòng (xem bước 2).
  - B: dịch 0.5σ với 89 mẫu nằm sát ngưỡng — KS có thể chưa đủ bằng chứng.
  - C: dịch 1σ → KS p-value rất nhỏ; Wasserstein ≈ 1.0 (đúng bằng độ dịch tính theo σ).
""")
