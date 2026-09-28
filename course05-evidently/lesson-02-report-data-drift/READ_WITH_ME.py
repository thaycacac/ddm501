"""
BÀI 02 — Evidently Report + DataDriftPreset
         (= tutorial07: evidently/main.py dòng 449–537, hàm perform_drift_analysis)

1) Ba khái niệm

   Metric   một phép tính (vd DatasetDriftMetric, DataDriftTable, ColumnDriftMetric)
   Preset   gói metric soạn sẵn: DataDriftPreset = tóm tắt dataset + bảng drift từng cột
   Report   danh sách metric/preset; .run() tính, rồi xuất ra nhiều dạng

       report = Report(metrics=[DataDriftPreset()])
       report.run(reference_data=ref_df, current_data=cur_df, column_mapping=None)
       report.save_html("x.html")   → cho người xem (histogram, bảng, màu)
       report.as_dict()             → cho code đọc
       report.json()                → như as_dict nhưng là chuỗi JSON (có thêm version, timestamp)

2) Cấu trúc as_dict()

   {"metrics": [
      {"metric": "DatasetDriftMetric",
       "result": {drift_share, number_of_columns, number_of_drifted_columns,
                  share_of_drifted_columns, dataset_drift}},
      {"metric": "DataDriftTable",
       "result": {..., "drift_by_columns": {
            "<cột>": {column_type, stattest_name, stattest_threshold,
                      drift_score, drift_detected, ...}}}}
   ]}
   → Tra metric theo TÊN (dict {tên: result}), đừng theo vị trí.

3) Các nút điều khiển của DataDriftPreset

   stattest= / num_stattest= / cat_stattest=   ép kiểm định (ks, wasserstein, psi, chisquare,
                                               jensenshannon, z, kl_div, ...)
   stattest_threshold= (và num_/cat_)          ngưỡng của kiểm định
   per_column_stattest= / per_column_stattest_threshold=   riêng từng cột
   drift_share=0.5                             tỷ lệ cột drift để kết luận "cả dataset drift"
   columns=[...]                               chỉ xét một số cột

   ColumnMapping(numerical_features=, categorical_features=, target=, prediction=)
   → khai báo kiểu cột thay vì để Evidently đoán (chuỗi, số nguyên ít giá trị hay bị đoán sai).
   tutorial07 không dùng ColumnMapping mà tự loại cột: exclude prediction, timestamp, model_version.

4) Soi tutorial07 (bước 2 chứng minh)

   - Cấp dataset: đọc đúng dataset_drift và share_of_drifted_columns.
   - Cấp cột: tìm drift_by_columns trong DatasetDriftMetric → không có → .get(..., {}) trả rỗng
     im lặng → drifted_features luôn [], drift_scores luôn {}, gauge FEATURE_DRIFT không bao giờ
     được set, DRIFTED_FEATURES_COUNT luôn 0. Chỗ đúng: result của "DataDriftTable".
   - Tham số threshold của perform_drift_analysis() không được truyền vào DataDriftPreset
     → đổi threshold trong request /analyze không có tác dụng (bài 04 sẽ sửa).
   - DataQualityPreset có chạy nhưng kết quả không được đọc (bài 03).

File:
  scripts/data.py                 bộ sinh dữ liệu mô phỏng tutorial07, trả DataFrame
  scripts/01_first_report.py      report đầu tiên, save_html, cấu trúc as_dict
  scripts/02_parse_as_dict.py     đọc đúng 2 cấp + chạy lại đoạn parse của tutorial07
  scripts/03_stattest_options.py  cỡ reference, ép kiểm định, ngưỡng, drift_share, ColumnMapping
  reports/                        HTML sinh ra (đã gitignore)

TỔNG KẾT
  - Report(metrics=[DataDriftPreset()]).run(reference_data, current_data) rồi save_html cho
    người, as_dict cho code.
  - DataDriftPreset = DatasetDriftMetric (cấp dataset) + DataDriftTable (drift_by_columns).
  - Kiểm định mặc định theo cỡ reference; ép bằng stattest / per_column_stattest; ngưỡng bằng
    stattest_threshold; kết luận dataset bằng drift_share.
  - Khai báo kiểu cột bằng ColumnMapping khi có cột chuỗi / số nguyên ít giá trị.
  - tutorial07 đọc drift từng cột sai metric → gauge theo feature luôn trống; threshold bị bỏ qua.
"""
print(__doc__)
