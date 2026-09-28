"""
BÀI 02 — Routing và grouping
         (= tutorial07: config/alertmanager/alertmanager.yml dòng 13–23)

1) Cây route

   route (gốc, receiver mặc định: team-chat, group_by [severity, component])
    ├─ audit-log   severity=~"critical|warning"   continue: true
    ├─ oncall      severity="critical"            repeat_interval: 1m
    └─ ml-team     component="model"

   - Duyệt route con theo THỨ TỰ, khớp cái đầu tiên thì dừng, trừ khi có `continue: true`.
   - Receiver gốc chỉ dùng khi KHÔNG route con nào khớp (route có continue cũng tính là khớp).
   - Route con kế thừa receiver/group_by/thời gian của cha, chỉ ghi đè cái nó khai báo.
   - matchers: `label="x"`, `label!="x"`, `label=~"regex"`, `label!~"regex"`; nhiều dòng = AND.

   Kết quả với cây trên:
     severity=critical component=api     → audit-log + oncall
     severity=critical component=model   → audit-log + oncall     (oncall dừng trước ml-team)
     severity=warning  component=model   → audit-log + ml-team
     severity=warning  component=api     → CHỈ audit-log           (bẫy: không về team-chat)
     severity=info     component=api     → team-chat

2) Gộp nhóm (group_by)

   Nhóm = các alert có cùng giá trị các label trong group_by → MỘT thông báo chứa nhiều alert.
   Mỗi route (mỗi receiver) giữ nhóm RIÊNG: một alert đi 2 nhánh → 2 thông báo.
   group_by [severity, component]: API chết kéo theo 3 alert critical/api → một tin, không phải 3.

3) Ba mốc thời gian (bài này: 10s / 30s / 3m, oncall ghi đè repeat = 1m)

   t=0      alert đầu tiên của nhóm MỚI đến
   t=10s    group_wait hết → gửi tin đầu tiên (gồm mọi alert đến trong 10s đó)
   t=15s    thêm alert vào nhóm → CHƯA gửi
   t=40s    group_interval (30s kể từ tin trước) → gửi tin cập nhật
   ...      không đổi gì → im lặng
   t≈3m40s  repeat_interval (3m) → nhắc lại. Chỉ xét ở nhịp group_interval nên lệch tối đa 30s.

   Tutorial07: 30s / 2m / 4h, route con cho critical chỉ để đổi repeat_interval thành 1h
   (cùng receiver telegram) — critical được nhắc dày hơn warning.

4) Công cụ

   amtool config routes show --config.file=...      in cây route
   amtool config routes test --config.file=... severity=critical component=api
                                                    → in receiver sẽ nhận, KHÔNG gửi gì cả
   scripts/fire.py  POST /api/v2/alerts với label tùy ý (thí nghiệm không cần chờ rule)

File:
  alertmanager/alertmanager.yml  cây route + 4 receiver (cùng về webhook-echo, khác tên)
  prometheus/alerts/api.yml      ApiDown, HighErrorRate có thêm label component=api
  scripts/fire.py                bắn / resolve alert giả
  docker-compose.yml             như bài 01, prometheus.yml dùng lại của bài 01

TỔNG KẾT
  - Route con duyệt theo thứ tự, khớp đầu tiên thì dừng; `continue: true` để đi tiếp.
  - Receiver gốc chỉ nhận khi không route con nào khớp — kể cả route có continue.
  - group_by quyết định alert nào chung một tin; mỗi receiver có nhóm riêng.
  - group_wait: chờ gom tin đầu. group_interval: khoảng cách tối thiểu giữa các tin cập nhật.
    repeat_interval: nhắc lại khi không đổi gì (xét theo nhịp group_interval).
  - Route con ghi đè được từng thiết lập (tutorial07: critical repeat 1h thay vì 4h).
  - Kiểm tra định tuyến bằng `amtool config routes test` trước khi chờ alert thật.
"""
print(__doc__)
