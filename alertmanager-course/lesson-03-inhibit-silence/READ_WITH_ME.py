"""
BÀI 03 — Inhibition và silence
         (= tutorial07: config/alertmanager/alertmanager.yml dòng 25–31)

Cả hai đều làm alert "im" (state=suppressed) nhưng KHÔNG đụng tới Prometheus: rule vẫn
firing, trang /alerts vẫn đỏ. Chỉ phần GỬI tin của Alertmanager bị chặn.

1) Inhibition — chặn TỰ ĐỘNG, khai báo trong config

   "Khi có alert NGUỒN đang firing thì đừng gửi alert ĐÍCH, nếu chúng cùng giá trị ở `equal`."
     source_matchers   alert nguồn (nguyên nhân)
     target_matchers   alert đích (hệ quả, bị chặn)
     equal             danh sách label phải trùng giá trị giữa nguồn và đích
   - Nguồn hết → đích tự hiện lại. Không cần ai làm gì.
   - Một alert không tự chặn chính nó (dù khớp cả source lẫn target).
   - Alert đích bị chặn không sinh tin "resolved" — nhóm chỉ im lặng.

   Rule A (tutorial07):  critical chặn warning, equal [alertname, component]
     → chỉ có tác dụng khi CÙNG alertname có hai mức. Tutorial07 đặt tên khác nhau cho
       hai mức nên rule này gần như vô hiệu. Muốn "critical chặn warning cùng component"
       thì bỏ alertname khỏi equal.
   Rule B (bài này):     ApiDown chặn mọi warning, equal [component]
     → API chết thì HighErrorRate/SlowPredictions của api là hệ quả, không cần báo thêm.

2) Silence — tắt TAY, tạm thời, lúc chạy

   Một silence = tập matchers + thời gian bắt đầu/kết thúc + người tạo + lý do.
   Alert (đang có hoặc đến sau) khớp matchers trong khoảng thời gian đó → không gửi.
   Dùng khi: bảo trì có kế hoạch, đã biết lỗi và đang sửa, alert ồn chưa kịp sửa rule.
   Tạo bằng: UI (tab Silences, hoặc nút "Silence" cạnh alert), amtool, API POST /api/v2/silences.
   Silence lưu ở --storage.path → restart không mất; hết hạn thì chuyển sang expired (vẫn xem lại được).

   So sánh:
                   inhibition                       silence
     ai tạo        người viết config                người trực, lúc chạy
     điều kiện     có alert nguồn đang firing       khớp matchers, trong khoảng thời gian
     kéo dài       tới khi nguồn hết                tới endsAt hoặc khi expire tay
     ở đâu         alertmanager.yml                 storage của Alertmanager (không nằm trong git)

3) Xem alert bị chặn vì đâu

   GET /api/v2/alerts → status.state = suppressed, status.inhibitedBy = [fingerprint nguồn],
   status.silencedBy = [id silence]. scripts/am_alerts.py (bài 01) in ra hai trường này.

File:
  alertmanager/alertmanager.yml  route đơn giản + 2 inhibit_rules
  amtool/config.yml              cấu hình amtool (url, author, bắt buộc comment)
  docker-compose.yml             như bài 02, mount thêm amtool/config.yml
  dùng lại: ../lesson-02-routing-grouping/scripts/fire.py, ../lesson-01-connect-prometheus/scripts/am_alerts.py

TỔNG KẾT
  - Inhibition: alert nguồn firing → chặn alert đích cùng giá trị `equal`. Tự động, hết khi nguồn hết.
  - `equal` quyết định phạm vi chặn; thêm alertname vào equal là thu hẹp tới mức gần như vô hiệu
    (lỗi của tutorial07).
  - Silence: tắt tay theo matchers + thời hạn + lý do; dùng khi bảo trì; tạo bằng UI/amtool/API.
  - Cả hai chỉ chặn việc GỬI; Prometheus vẫn firing; alert trong Alertmanager có state=suppressed
    kèm inhibitedBy / silencedBy.
"""
print(__doc__)
