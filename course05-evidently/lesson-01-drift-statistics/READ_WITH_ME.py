"""
BÀI 01 — Thống kê của drift (tự tính bằng scipy, chưa dùng Evidently)
         (= tutorial07: ý nghĩa các con số drift_score / share_of_drifted_columns trong
            evidently/main.py dòng 490–513, và dữ liệu sinh từ simulations/data_generator.py)

1) Reference vs current

   reference  dữ liệu "chuẩn": tập train, hoặc một giai đoạn production đã biết là tốt
   current    cửa sổ dữ liệu gần đây (tutorial07: 100 request cuối, window_size=100)
   Câu hỏi: "current có đến từ CÙNG phân phối với reference không?" — hỏi riêng TỪNG feature.

   Khác prometheus-course bài 09: ở đó đo drift ĐẦU RA (tỷ lệ dự đoán lệch baseline).
   Ở đây đo drift ĐẦU VÀO (data drift) — phát hiện được cả khi đầu ra chưa kịp đổi.

2) Hai họ phép đo — ĐỌC NGƯỢC CHIỀU NHAU

   | Phép đo              | Kiểu dữ liệu | Trả về      | Drift khi      |
   |----------------------|--------------|-------------|----------------|
   | KS (Kolmogorov–Smirnov) | số        | p-value     | p < 0.05       |
   | Chi-square           | phân loại    | p-value     | p < 0.05       |
   | Z-test tỷ lệ         | binary       | p-value     | p < 0.05       |
   | Wasserstein (normed) | số           | khoảng cách | >= 0.1         |
   | Jensen-Shannon       | phân loại    | khoảng cách | >= 0.1         |

   p-value: "nếu không có drift, thấy chênh lệch cỡ này hiếm đến mức nào" → đo ĐỘ CHẮC CHẮN.
   Khoảng cách: "hai phân phối cách nhau bao xa" → đo ĐỘ LỚN của thay đổi.

3) Cỡ mẫu đổi kết luận của p-value (bước 2, 3)

   Mẫu lớn → p-value tí hon cả với thay đổi vô hại → báo động liên tục.
   Mẫu nhỏ → khoảng cách bị nhiễu đẩy lên → báo động giả.
   Nên Evidently 0.4.x chọn kiểm định mặc định theo cỡ REFERENCE:

     feature số,       reference <= 1000 → KS             > 1000 → Wasserstein normed
     feature phân loại, reference <= 1000 → chi-square     > 1000 → Jensen-Shannon
                        (chỉ 2 giá trị → Z-test)
     feature số nhưng <= 5 giá trị khác nhau → coi như phân loại

   Có thể ép kiểm định/ngưỡng khác (stattest=, stattest_threshold=) — bài 02.

4) Từ từng feature lên cả dataset

   drift_detected (từng cột)   = kết luận của kiểm định cột đó
   share_of_drifted_columns    = số cột drift / tổng số cột
   dataset_drift               = share >= 0.5  (drift_share mặc định 0.5)

5) Ánh xạ vào tutorial07

   - Dữ liệu: reference vài trăm dòng, window 100 → Evidently dùng KS cho feature số
     → "drift_score" của từng feature là P-VALUE (nhỏ = drift), không phải "điểm drift".
   - DRIFT_SCORE (gauge của cả dataset) lại là share_of_drifted_columns — và chỉ được set
     khi dataset_drift=True, ngược lại set 0. Cùng chữ "score", hai nghĩa khác nhau.
   - Bộ sinh dữ liệu: drift = mean × multiplier cho vài feature NGẪU NHIÊN mỗi mẫu → current
     là hỗn hợp; "slight_drift" có feature dịch tới ~4σ (bước 4).

File:
  scripts/01_numeric_tests.py        KS + Wasserstein trên cột alcohol, histogram ASCII
  scripts/02_sample_size.py          cùng độ lệch, đổi n: p-value đổi, khoảng cách không
  scripts/03_categorical_tests.py    chi-square + Jensen-Shannon, cả trường hợp mẫu lớn
  scripts/04_tutorial07_scenarios.py mô phỏng 5 kịch bản tutorial07, tính dataset_drift bằng tay

TỔNG KẾT
  - Drift = current không còn cùng phân phối với reference; kiểm tra TỪNG feature.
  - p-value (KS, chi-square, Z): nhỏ = drift, ngưỡng 0.05, nhạy cỡ mẫu.
    Khoảng cách (Wasserstein normed, Jensen-Shannon): lớn = drift, ngưỡng 0.1, đo độ lớn.
  - Evidently chọn kiểm định theo cỡ reference: <= 1000 dòng dùng p-value, > 1000 dùng khoảng cách.
  - dataset_drift = tỷ lệ cột drift >= 0.5.
  - Đọc "drift_score" phải biết kiểm định nào sinh ra nó; tutorial07 dùng KS → đó là p-value.
"""
print(__doc__)
