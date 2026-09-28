"""
Bước 2 — TestSuite: biến số đo thành PASS/FAIL bằng điều kiện tự viết.

Cùng dữ liệu bẩn như bước 1.

Chạy: ../.venv/bin/python scripts/02_test_suite.py
"""
import warnings
from pathlib import Path

from evidently.test_suite import TestSuite
from evidently.tests import (
    TestColumnDrift,
    TestColumnShareOfMissingValues,
    TestColumnValueMax,
    TestColumnValueMin,
    TestNumberOfConstantColumns,
    TestNumberOfDuplicatedRows,
    TestNumberOfRows,
    TestShareOfDriftedColumns,
)

from data import inject_quality_issues, make_batch

warnings.filterwarnings("ignore")

reference = make_batch(500, "normal", seed=1)
current = inject_quality_issues(make_batch(100, "normal", seed=2))

# Mỗi test = một số đo + một điều kiện. Điều kiện viết bằng tham số:
#   eq, not_eq, gt, gte, lt, lte, is_in, not_in
# Không ghi điều kiện → Evidently tự suy từ reference (bước 3).
# is_critical=False → trượt thì ra WARNING thay vì FAIL (không chặn pipeline).
suite = TestSuite(tests=[
    TestNumberOfRows(gte=100),                                   # đủ mẫu mới đáng phân tích
    TestColumnShareOfMissingValues(column_name="alcohol", lte=0.05),
    TestColumnValueMin(column_name="pH", gte=2.74),              # miền hợp lệ từ config tutorial07
    TestColumnValueMax(column_name="pH", lte=4.01),
    TestNumberOfConstantColumns(eq=0),
    TestNumberOfDuplicatedRows(eq=0, is_critical=False),         # trùng: cảnh báo, không chặn
    TestColumnDrift(column_name="alcohol"),                      # dùng kiểm định mặc định (KS)
    TestShareOfDriftedColumns(lt=0.5),                           # = dataset_drift của bài 02
])
suite.run(reference_data=reference, current_data=current)

out = Path(__file__).resolve().parent.parent / "reports"
out.mkdir(exist_ok=True)
suite.save_html(str(out / "test_suite.html"))

result = suite.as_dict()
print(f"{'STATUS':<8} | {'TEST':<45} | mô tả")
print("-" * 110)
for t in result["tests"]:
    print(f"{t['status']:<8} | {t['name']:<45} | {t['description'][:60]}")

s = result["summary"]
print(f"\nsummary: all_passed={s.get('all_passed')}  total={s.get('total_tests')}"
      f"  success={s.get('success_tests')}  failed={s.get('failed_tests')}")
print(f"by_status: {s.get('by_status')}")

print(f"""
Đã lưu {out / 'test_suite.html'}

Đọc kết quả:
  - Mỗi test có status: SUCCESS / FAIL / WARNING / ERROR / SKIPPED.
  - Duplicated rows trượt nhưng chỉ WARNING vì is_critical=False → all_passed vẫn tính theo FAIL.
  - alcohol thiếu 20% vẫn có thể "không drift": missing và drift là hai câu hỏi khác nhau.
  - as_dict()["summary"]["all_passed"] là MỘT boolean — đúng thứ mà Airflow/CI cần để
    quyết định chạy tiếp hay dừng.
""")
