"""
BÀI 09 — Monitoring riêng cho ML: khi service khỏe mà câu trả lời đổi
         (= tutorial06: MALIGNANT_SHARE trong app/metrics.py, deque trong app/main.py,
            panel 4, alert MalignantShareShift, bài tập 4, câu 6 của checklist;
            dẫn sang tutorial07 — Evidently)

Dùng lại stack bài 08 (api + prometheus + grafana).

1) Hai loại hỏng

   Hỏng KỸ THUẬT   chết, lỗi, chậm            → up, error share, p95   (web service nào cũng có)
   Hỏng ML         chạy tốt, trả lời SAI dần   → không có lỗi nào để đếm
   --drift 3.0 ở bài 07–08: latency phẳng, lỗi 0%, container healthy — và model trả lời
   khác hẳn lúc deploy. Mọi alert web thông thường đều im lặng.

2) Các kiểu drift

   Data drift (covariate shift)   phân bố INPUT đổi: máy đo mới, nhóm bệnh nhân khác, lỗi ETL
   Prediction drift               phân bố OUTPUT đổi: tỉ lệ ác tính 37% → 90%
   Concept drift                  quan hệ input → nhãn đổi: cùng input, đáp án đúng đã khác
   Concept drift chỉ đo được khi có NHÃN THẬT. Nhãn đến muộn (kết quả sinh thiết sau vài
   tuần) → trong lúc chờ, theo dõi thứ có ngay: phân bố dự đoán — một PROXY.

3) Baseline — "bình thường" là bao nhiêu?

   Tỉ lệ ác tính lúc train = 0.374 (train_malignant_share trong model_card.json của bài 03).
   Tutorial06 viết cứng 0.37 vào alert. Deploy model mới → baseline phải cập nhật theo.

4) Ngưỡng — lệch bao nhiêu mới đáng báo?

   wdbc_malignant_share tính trên 200 dự đoán gần nhất. Dù dữ liệu không đổi, tỉ lệ vẫn dao
   động ngẫu nhiên: độ lệch chuẩn của tỉ lệ = sqrt(p(1−p)/n) = sqrt(0.37·0.63/200) ≈ 0.034.
   Ngưỡng 0.15 ≈ 4.4 lần độ lệch chuẩn → gần như không bao giờ báo nhầm vì nhiễu.
   Cửa sổ nhỏ hơn (n=50) → độ lệch ≈ 0.068 → ngưỡng 0.15 chỉ còn ~2.2σ → báo nhầm thường xuyên.
   Cộng thêm `for: 15m` → phải lệch LIÊN TỤC 15 phút.

5) Cửa sổ theo SỐ LƯỢNG (deque) và cửa sổ theo THỜI GIAN (PromQL)

   deque(maxlen=200)        200 dự đoán gần nhất. Traffic thấp → trải hàng giờ; cao → vài giây.
                            Reset khi restart (nằm trong RAM của process).
   PromQL từ counter        sum(rate(wdbc_predictions_total{outcome="malignant"}[15m]))
                            / sum(rate(wdbc_predictions_total[15m]))
                            → tỉ lệ trong 15 PHÚT qua, sống qua restart, gộp nhiều instance.
   Có nhiều instance thì cách PromQL đúng hơn: mỗi instance có deque riêng.

6) Giới hạn của một con số

   Tỉ lệ dự đoán có thể KHÔNG đổi trong khi input đã lệch (lệch theo hướng model không nhạy,
   hoặc hai nhóm lệch ngược chiều bù nhau). Muốn chắc: theo dõi phân bố TỪNG FEATURE
   (trung bình, PSI, kiểm định KS...) so với dữ liệu train. Đó là việc của công cụ như
   Evidently — tutorial07 xuất các chỉ số drift đó ra Prometheus và dùng lại y hệt kỹ năng
   PromQL / alert / Grafana của khóa này.

File:
  scripts/drift_sweep.py   bắn 250 request ở từng mức drift, in tỉ lệ ác tính và alert có kêu không
  queries.promql           so sánh cửa sổ deque với cửa sổ PromQL, khoảng cách tới baseline

TỔNG KẾT
  - Service ML hỏng được theo cách không có lỗi nào: chạy tốt, trả lời khác. Alert web im lặng.
  - Data drift (input), prediction drift (output), concept drift (cần nhãn thật — đến muộn).
  - Khi chưa có nhãn: theo dõi phân bố dự đoán làm proxy (wdbc_malignant_share).
  - Baseline lấy từ dữ liệu train (0.37); đổi model → đổi baseline.
  - Ngưỡng chọn theo nhiễu thống kê: σ = sqrt(p(1−p)/n); 0.15 với n=200 ≈ 4.4σ. Thêm for: dài.
  - deque = cửa sổ theo số lượng, mất khi restart; PromQL rate = cửa sổ theo thời gian, gộp instance.
  - Một con số tổng hợp có thể bỏ sót drift → theo dõi từng feature (Evidently, tutorial07).
"""
print(__doc__)
