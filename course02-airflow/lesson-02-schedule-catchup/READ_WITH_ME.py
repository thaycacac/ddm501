"""
BÀI 02 — Lịch chạy: schedule, start_date, catchup, logical date / ds
         (= tutorial04 wdbc_pipeline.py dòng 38–51)

1) Airflow chạy theo KHOẢNG DỮ LIỆU (data interval), không theo "bây giờ"

   schedule="@daily" chia thời gian thành các khoảng 1 ngày (giờ UTC):

     [09-25 00:00, 09-26 00:00)  [09-26 00:00, 09-27 00:00)  [09-27 00:00, ...
          ds = 2026-09-25             ds = 2026-09-26            (chưa xong)

   - Một DAG run xử lý MỘT khoảng.
   - Run chỉ được tạo khi khoảng đó ĐÃ KẾT THÚC (dữ liệu của ngày 26 chỉ đủ
     sau 00:00 ngày 27).
   - logical_date = ĐẦU khoảng. ds = logical_date dạng "YYYY-MM-DD".
     → Run có ds=2026-09-26 thật ra chạy vào ngày 27. Đây là chỗ hay nhầm nhất.
   - Giờ Việt Nam = UTC+7 → ngày UTC mới bắt đầu lúc 07:00 sáng giờ VN.

   Task nhận các giá trị này bằng cách khai báo tham số TRÙNG TÊN, mặc định None:
       def my_task(ds: str = None, data_interval_start=None, ...)
   (tutorial04: mọi task đều có  ds: str = None  → dùng ds đặt tên thư mục.)

2) start_date + catchup
   start_date : khoảng đầu tiên bắt đầu từ đây. Nên là ngày CỐ ĐỊNH, không dùng now().
   catchup=True : bật DAG lên → tạo run cho MỌI khoảng đã qua từ start_date tới nay.
   catchup=False: chỉ tạo run cho khoảng GẦN NHẤT đã kết thúc, bỏ qua quá khứ.
   max_active_runs=1 : mỗi lúc chỉ 1 run của DAG này đang chạy → chạy bù lần lượt.

   Tutorial04: start_date 2026-08-20, catchup=False, max_active_runs=1
   → bật lên không chạy bù cả tháng; muốn chạy bù thì dùng backfill (bài 04).

3) Các giá trị schedule hay gặp
   None                 chỉ chạy khi trigger (bài 01)
   "@daily" "@hourly" "@weekly"   preset
   "0 6 * * *"          cron: 06:00 UTC mỗi ngày
   timedelta(hours=6)   cứ 6 tiếng một lần

4) run_id cho biết run sinh ra thế nào
   scheduled__2026-09-26T00:00:00+00:00   scheduler tạo theo lịch
   manual__...                            trigger tay / dags test
   backfill__...                          chạy bù bằng CLI (bài 04)

File trong bài:
  docker-compose.yml             như bài 01 nhưng dùng lại image, không build
  dags/catchup_true_dag.py       @daily, start 2026-09-20, catchup=True
  dags/catchup_false_dag.py      giống hệt, chỉ khác catchup=False
"""
print(__doc__)
