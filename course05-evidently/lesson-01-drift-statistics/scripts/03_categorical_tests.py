"""
Bước 3 — Feature PHÂN LOẠI (category): chi-square và Jensen-Shannon.

Dùng cột `target` của wine (3 giống nho: 0, 1, 2) như một feature phân loại.
Với category không có "trung bình" hay "dịch σ" — chỉ có TỶ LỆ từng giá trị.

Chạy: ../.venv/bin/python scripts/03_categorical_tests.py
"""
import numpy as np
from scipy import stats
from scipy.spatial import distance
from sklearn.datasets import load_wine

rng = np.random.default_rng(42)
CATEGORIES = [0, 1, 2]

target = load_wine(as_frame=True).frame["target"].to_numpy()
order = rng.permutation(len(target))
reference = target[order[:89]]
current_same = target[order[89:]]
# current lệch: phần lớn là giống 0 (giả lập nguồn nhập hàng thay đổi)
current_skewed = rng.choice(CATEGORIES, size=89, p=[0.6, 0.3, 0.1])


def counts(x):
    return np.array([(x == c).sum() for c in CATEGORIES])


def compare(label, ref, cur):
    ref_c, cur_c = counts(ref), counts(cur)
    ref_p, cur_p = ref_c / ref_c.sum(), cur_c / cur_c.sum()

    # Chi-square goodness-of-fit (cách Evidently làm):
    #   "nếu current theo đúng tỷ lệ của reference thì mỗi ô kỳ vọng có bao nhiêu mẫu?"
    #   f_exp = tỷ lệ reference × số mẫu current; so với số đếm thực tế f_obs.
    #   → p-value NHỎ = DRIFT (drift khi p < 0.05), cũng nhạy cỡ mẫu như KS.
    f_exp = ref_p * cur_c.sum()
    chi = stats.chisquare(f_obs=cur_c, f_exp=f_exp)

    # Jensen-Shannon distance: khoảng cách giữa 2 phân phối xác suất, trong [0, 1]
    # (dạng đối xứng, có chặn của KL divergence).
    #   → khoảng cách LỚN = DRIFT (drift khi >= 0.1)
    js = distance.jensenshannon(ref_p, cur_p)

    print(f"\n=== {label} ===")
    print(f"  tỷ lệ reference: {np.round(ref_p, 3)}   (n={ref_c.sum()})")
    print(f"  tỷ lệ current  : {np.round(cur_p, 3)}   (n={cur_c.sum()})")
    print(f"  chi-square     stat={chi.statistic:.3f}  p-value={chi.pvalue:.4g}"
          f"  → drift={chi.pvalue < 0.05}")
    print(f"  Jensen-Shannon {js:.3f}  → drift={js >= 0.1}")


compare("A. current = nửa còn lại (không drift)", reference, current_same)
compare("B. current lệch về giống 0", reference, current_skewed)

# C. Cỡ mẫu lớn + lệch rất nhỏ: chi-square vẫn "la làng", JS thì bình thản
big_ref = rng.choice(CATEGORIES, size=50000, p=[0.33, 0.40, 0.27])
big_cur = rng.choice(CATEGORIES, size=50000, p=[0.35, 0.39, 0.26])
compare("C. 50000 mẫu, tỷ lệ lệch 1–2 điểm %", big_ref, big_cur)

print("""
Đọc kết quả:
  - A: không drift → chi-square p lớn, JS nhỏ.
  - B: lệch rõ → cả hai đều báo drift.
  - C: giống hệt câu chuyện KS/Wasserstein ở bước 2: mẫu lớn làm p-value tí hon cho một lệch
    vô hại. Vì vậy Evidently dùng chi-square khi reference <= 1000 dòng, Jensen-Shannon khi lớn hơn.
  - Category chỉ có 2 giá trị (binary) và reference <= 1000 → Evidently dùng Z-test cho tỷ lệ.
""")
