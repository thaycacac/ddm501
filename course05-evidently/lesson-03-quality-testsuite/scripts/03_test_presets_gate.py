"""
Bước 3 — Test preset (điều kiện TỰ SUY từ reference) + dùng TestSuite làm "cổng chặn".

Chạy:
  ../.venv/bin/python scripts/03_test_presets_gate.py;                                   echo "exit=$?"
  ../.venv/bin/python scripts/03_test_presets_gate.py --current-size 500;                echo "exit=$?"
  ../.venv/bin/python scripts/03_test_presets_gate.py --current-size 500 --dirty;        echo "exit=$?"
  ../.venv/bin/python scripts/03_test_presets_gate.py --current-size 500 --scenario slight_drift; echo "exit=$?"
"""
import argparse
import sys
import warnings
from collections import Counter

from evidently.test_preset import DataDriftTestPreset, DataQualityTestPreset, DataStabilityTestPreset
from evidently.test_suite import TestSuite

from data import SCENARIOS, inject_quality_issues, make_batch

warnings.filterwarnings("ignore")

parser = argparse.ArgumentParser()
parser.add_argument("--scenario", choices=list(SCENARIOS), default="normal")
parser.add_argument("--current-size", type=int, default=100, help="số dòng current (tutorial07: 100)")
parser.add_argument("--dirty", action="store_true", help="làm bẩn current (missing, pH=-1, ...)")
parser.add_argument("--verbose", action="store_true", help="in cả test SUCCESS")
args = parser.parse_args()

reference = make_batch(500, "normal", seed=1)
current = make_batch(args.current_size, args.scenario, seed=2)
if args.dirty:
    current = inject_quality_issues(current)

# Preset sinh sẵn nhiều test, điều kiện lấy từ reference, ví dụ:
#   DataStabilityTestPreset  số dòng/cột, kiểu cột, miền giá trị, mean trong ±2σ của reference
#   DataQualityTestPreset    missing, trùng, hằng số, tương quan...
#   DataDriftTestPreset      drift từng cột + tỷ lệ cột drift
# Bẫy: điều kiện tự suy giả định current "giống cỡ" reference (vd số dòng ≈ reference ±10%).
# reference 500 dòng mà current chỉ 100 (window của tutorial07) → TestNumberOfRows trượt dù
# dữ liệu hoàn toàn bình thường. Ở production nên tự viết điều kiện như bước 2.
suite = TestSuite(tests=[DataStabilityTestPreset(), DataQualityTestPreset(), DataDriftTestPreset()])
suite.run(reference_data=reference, current_data=current)
result = suite.as_dict()

statuses = Counter(t["status"] for t in result["tests"])
print(f"scenario={args.scenario} current={len(current)} dòng dirty={args.dirty}"
      f" → {len(result['tests'])} test: {dict(statuses)}")
for t in result["tests"]:
    if args.verbose or t["status"] != "SUCCESS":
        print(f"  {t['status']:<8} {t['name']:<40} {t['description'][:70]}")

passed = result["summary"]["all_passed"]
print(f"\nall_passed={passed}")

# Cổng chặn: exit code khác 0 → Airflow đánh task failed / CI dừng build.
# Airflow bài 10: DAG train lại dùng đúng ý này để quyết định có promote model hay không.
sys.exit(0 if passed else 1)
