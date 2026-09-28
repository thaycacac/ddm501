"""
Bộ sinh dữ liệu dùng chung cho các script của bài — mô phỏng lại
tutorial07/simulations/data_generator.py (giống bước 4 bài 01) nhưng trả về pandas DataFrame,
vì Evidently nhận DataFrame.
"""
import numpy as np
import pandas as pd

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


def make_batch(n: int, scenario: str = "normal", seed: int = 0) -> pd.DataFrame:
    """Sinh n dòng theo kịch bản; cùng seed → cùng dữ liệu."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        row = {f: float(np.clip(rng.normal(mean, std), lo, hi))
               for f, (lo, hi, mean, std) in FEATURES.items()}
        if SCENARIOS[scenario]:
            mult, noise, k = SCENARIOS[scenario]
            for f in rng.choice(NAMES, size=k, replace=False):
                lo, hi, mean, std = FEATURES[f]
                row[str(f)] = float(np.clip(mean * mult + rng.normal(0, std * noise), lo, hi))
        rows.append(row)
    return pd.DataFrame(rows, columns=NAMES)
