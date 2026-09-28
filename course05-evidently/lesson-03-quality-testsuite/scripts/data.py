"""
Dùng lại bộ sinh dữ liệu của bài 02, thêm hàm "làm bẩn" dữ liệu để có lỗi chất lượng.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

# File bài 02 cũng tên data.py → không `import data` được (trùng tên chính file này),
# nên nạp theo đường dẫn dưới một tên khác.
_path = Path(__file__).resolve().parents[2] / "lesson-02-report-data-drift" / "scripts" / "data.py"
_spec = importlib.util.spec_from_file_location("lesson02_data", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

FEATURES, NAMES, SCENARIOS, make_batch = _mod.FEATURES, _mod.NAMES, _mod.SCENARIOS, _mod.make_batch


def inject_quality_issues(df: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Giả lập 4 lỗi hay gặp ở production — KHÔNG phải drift, mà là dữ liệu hỏng."""
    rng = np.random.default_rng(seed)
    df = df.copy()
    # 1) 20% dòng thiếu alcohol (client quên gửi / parse lỗi)
    idx = rng.choice(len(df), size=int(0.2 * len(df)), replace=False)
    df.loc[idx, "alcohol"] = np.nan
    # 2) 5 dòng pH = -1 (giá trị "lính canh" khi cảm biến lỗi — ngoài miền hợp lệ 2.74–4.01)
    df.loc[:4, "pH"] = -1.0
    # 3) sulphates thành hằng số (pipeline upstream điền giá trị mặc định cho mọi dòng)
    df["sulphates"] = 0.66
    # 4) 10 dòng trùng (client retry gửi lại 2 lần)
    return pd.concat([df, df.iloc[:10]], ignore_index=True)
