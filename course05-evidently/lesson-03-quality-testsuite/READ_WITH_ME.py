"""
BÀI 03 — DataQualityPreset + TestSuite
         (= tutorial07: evidently/main.py dòng 473–476 — DataQualityPreset có chạy nhưng
            kết quả bị bỏ qua; và nền tảng cho "quality gate" của DAG model_retrain)

1) Hai câu hỏi khác nhau

   Drift       "dữ liệu có ĐỔI so với reference không?"  (bài 01–02)
   Chất lượng  "dữ liệu có HỎNG không?"  missing, trùng dòng, cột hằng, giá trị ngoài miền
   Dữ liệu hỏng có thể KHÔNG drift (alcohol thiếu 20% nhưng phần còn lại vẫn cùng phân phối),
   và drift có thể KHÔNG hỏng (slight_drift: số liệu sạch, chỉ dịch). Cần kiểm tra cả hai.

2) DataQualityPreset (Report)

   Bung ra: DatasetSummaryMetric (đếm dòng, missing, trùng, cột hằng...), ColumnSummaryMetric
   cho TỪNG cột (count, missing%, min, mean, max, unique...), cùng vài metric missing/tương quan.
   Report chỉ ĐO — không kết luận đạt/trượt.

3) TestSuite = số đo + điều kiện → SUCCESS / FAIL / WARNING / ERROR / SKIPPED

       suite = TestSuite(tests=[TestColumnValueMin(column_name="pH", gte=2.74), ...])
       suite.run(reference_data=ref, current_data=cur)
       suite.as_dict()["summary"]["all_passed"]    → một boolean

   Điều kiện: eq, not_eq, gt, gte, lt, lte, is_in, not_in.
   Không ghi điều kiện → tự suy từ reference (vd số dòng ≈ reference ±10%, mean trong ±2σ).
   is_critical=False → trượt thì WARNING, không làm all_passed = False.

   Test preset: DataStabilityTestPreset, DataQualityTestPreset, DataDriftTestPreset
   (và NoTargetPerformanceTestPreset...) — tiện để bắt đầu, nhưng điều kiện tự suy rất khắt khe:
     - số dòng ≈ reference ±10% → window 100 vs reference 500 trượt oan
     - out-of-range eq=0 → chỉ 1/500 giá trị vượt min/max của reference là FAIL
     - share of most common value, max correlation so với reference ±10% → dữ liệu bị clip
       (nhiều giá trị dồn ở min/max) hoặc tương quan dao động tự nhiên cũng FAIL
   Kết quả thực tế: cả dữ liệu SẠCH 500 dòng cũng trượt 16/63 test → preset không dùng thẳng
   làm cổng chặn được; cổng chặn thật phải tự viết điều kiện (bước 2).

4) Report hay TestSuite?

   Report     xem, điều tra, dashboard, xuất số cho Prometheus (tutorial07 dùng cái này)
   TestSuite  cổng chặn tự động: bước kiểm tra dữ liệu trong Airflow trước khi train,
              quality gate trước khi promote model, CI — exit code 1 khi all_passed=False

File:
  scripts/data.py                    nạp bộ sinh dữ liệu bài 02 + inject_quality_issues()
  scripts/01_data_quality_report.py  DataQualityPreset trên dữ liệu bẩn, so reference/current
  scripts/02_test_suite.py           TestSuite tự viết điều kiện, is_critical, summary
  scripts/03_test_presets_gate.py    test preset + exit code làm cổng chặn

TỔNG KẾT
  - Drift ≠ chất lượng: kiểm tra cả "có đổi không" và "có hỏng không".
  - DataQualityPreset đo missing/trùng/hằng/min-max từng cột; Report không phán đạt/trượt.
  - TestSuite = số đo + điều kiện (gte, lte, eq...) → status; all_passed là một boolean.
  - is_critical=False để cảnh báo mà không chặn. Test preset với điều kiện tự suy trượt cả dữ
    liệu sạch → chỉ dùng để khám phá; cổng chặn thật phải tự viết điều kiện.
  - Report cho quan sát/metric; TestSuite cho cổng chặn trong Airflow/CI.
  - tutorial07 chạy DataQualityPreset nhưng không đọc → lỗi chất lượng không bao giờ được báo.
"""
print(__doc__)
