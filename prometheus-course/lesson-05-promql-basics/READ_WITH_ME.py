"""
BÀI 05 — PromQL cơ bản: selector, rate, sum by, tỉ lệ lỗi
         (= tutorial06: panel 1 "Predictions per second" và panel 2 "Error share"
            trong monitoring/grafana/dashboards/wdbc.json; alert HighErrorRate
            trong monitoring/prometheus/alerts/model.yml; bài tập 3 của README)

Dùng lại stack bài 04 (api + prometheus). Không có code mới để chạy — bài này là
NGÔN NGỮ truy vấn. Các câu truy vấn nằm trong queries.promql, theo thứ tự học.

1) Hai kiểu dữ liệu chính

   Instant vector   mỗi series MỘT giá trị, tại một thời điểm.
                    wdbc_predictions_total            → 2 series, mỗi series 1 số
   Range vector     mỗi series NHIỀU giá trị trong một khoảng thời gian gần nhất.
                    wdbc_predictions_total[1m]        → mỗi series ~12 điểm (scrape 5s)
   Range vector không vẽ được trực tiếp — nó là NGUYÊN LIỆU cho hàm như rate().

2) Selector — chọn series theo label

   wdbc_errors_total{reason="missing_features"}     bằng
   wdbc_predictions_total{outcome!="benign"}        khác
   up{job=~"wdbc.*"}                                 khớp regex
   {job="wdbc-api"}                                  mọi metric của job đó

3) rate() — thứ bạn đã tự tính ở bài 01

   rate(wdbc_predictions_total[1m])
   = (giá trị cuối − giá trị đầu trong 1 phút) / số giây, có xử lý counter reset.
   → "trung bình bao nhiêu mỗi giây trong 1 phút qua".
   - CHỈ dùng rate() cho Counter. Gauge lên xuống → rate vô nghĩa.
   - Cửa sổ nên >= 4 lần scrape_interval (5s → tối thiểu ~20s). [1m] là an toàn.
     Cửa sổ ngắn → nhạy nhưng giật; dài → mượt nhưng phản ứng chậm.
   - increase(x[5m]) = rate(x[5m]) * 300 → "tăng bao nhiêu trong 5 phút".

4) Aggregation — gộp nhiều series

   sum(rate(wdbc_predictions_total[1m]))                     tổng mọi outcome → 1 series
   sum by (outcome) (rate(wdbc_predictions_total[1m]))       giữ lại label outcome
   sum without (instance) (...)                              bỏ label instance, giữ phần còn lại
   Quy tắc vàng: RATE TRƯỚC, SUM SAU. sum() trước rồi rate() sẽ làm hỏng việc
   phát hiện counter reset (một instance restart → tổng giảm → rate sai).
   Khác: avg, min, max, count, topk(3, ...).

5) Phép toán giữa hai vector — khớp theo label

   A / B chỉ ghép những series có CÙNG TẬP LABEL ở hai bên.
     wdbc_errors_total có label reason, wdbc_predictions_total có label outcome
     → không cặp nào khớp → chia trực tiếp ra KẾT QUẢ RỖNG.
   Cách làm: sum() cả hai bên để bỏ hết label khác nhau rồi mới chia:

     sum(rate(wdbc_errors_total[5m]))
     /
     (sum(rate(wdbc_errors_total[5m])) + sum(rate(wdbc_predictions_total[5m])))

   = tỉ lệ lỗi trong 5 phút qua. Đúng công thức alert HighErrorRate của tutorial06.
   Tỉ lệ, không phải số đếm: 40 lỗi là bình thường với 10.000 request, là thảm họa với 100.

6) So sánh = lọc

   <biểu thức> > 0.05     chỉ giữ series có giá trị > 0.05; không có → kết quả rỗng.
   Alert của Prometheus chính là: "biểu thức này có trả về series nào không?" (bài 07).

7) Gauge dùng hàm *_over_time, không dùng rate

   avg_over_time(wdbc_malignant_share[5m])     trung bình 5 phút
   max_over_time(...), min_over_time(...)

8) offset — so với quá khứ

   sum(rate(wdbc_predictions_total[1m] offset 5m))   giá trị của 5 phút trước
   Câu "có chậm hơn thứ Ba tuần trước không?" = cùng biểu thức với offset 7d.

File:
  queries.promql         các câu truy vấn theo thứ tự học, mỗi câu có comment
  scripts/promql.py      chạy một câu PromQL từ terminal qua HTTP API (/api/v1/query)
                         — cùng API mà Grafana dùng (bài 08)

TỔNG KẾT
  - Instant vector = 1 giá trị/series (vẽ được). Range vector [1m] = nhiều giá trị/series,
    chỉ để đưa vào hàm.
  - Selector {label="..."} với =, !=, =~, !~ để chọn series.
  - Counter → luôn bọc rate(x[cửa sổ]) (/giây) hoặc increase (tổng trong cửa sổ).
    Cửa sổ >= 4 × scrape_interval.
  - sum / sum by (label) / sum without (label) để gộp. Rate trước, sum sau.
  - Phép toán giữa hai vector khớp theo TẬP LABEL; label khác nhau → rỗng → sum() hai bên trước.
  - Tỉ lệ lỗi = sum(rate(errors)) / (sum(rate(errors)) + sum(rate(predictions))).
  - So sánh (> 0.05) là bộ lọc; alert = "biểu thức có trả về gì không".
  - Gauge → avg/max/min_over_time, không rate. offset để so với quá khứ.
  - Tutorial06: panel 1 = sum by (outcome)(rate(...[1m])), panel 2 = tỉ lệ lỗi [1m],
    HighErrorRate = tỉ lệ lỗi [5m] > 0.05.
"""
print(__doc__)
