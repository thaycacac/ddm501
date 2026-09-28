"""
BÀI 05 — In các dòng bị cách ly + báo cáo validation của một ngày.

  docker compose exec airflow python /opt/airflow/scripts/show_rejected.py 2026-09-27
"""
import json
import sys
from pathlib import Path

import pandas as pd

ds = sys.argv[1]
d = Path("/opt/airflow/data/staging") / ds

print(json.dumps(json.loads((d / "validation_report.json").read_text()), indent=2))
print("\nrejected.parquet:")
print(pd.read_parquet(d / "rejected.parquet").to_string(index=False))
