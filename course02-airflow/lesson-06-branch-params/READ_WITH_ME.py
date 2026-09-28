"""
BÀI 06 — Rẽ nhánh và tham số
         (= tutorial07/airflow_dags/drift_monitoring.py: params dòng 39–44, run_drift_analysis
            dòng 48–71, decide dòng 73–77, no_drift / nối task dòng 99–104)

1) Param — tham số có kiểu của DAG

   params={"threshold": Param(0.1, type="number", minimum=0, maximum=1, description="...")}
   type: "number" | "integer" | "string" | "boolean" | "array" | "object"; thêm enum=[...],
   minimum/maximum, minLength... (chuẩn JSON Schema).

   Giá trị đến từ đâu:
     chạy theo lịch             → giá trị mặc định
     Trigger trên UI            → form sinh từ Param (ô số, checkbox, dropdown cho enum)
     CLI / API kèm conf         → airflow dags trigger X --conf '{"threshold": 0.5}'
   conf ghi đè mặc định rồi bị KIỂM TRA; sai kiểu / ngoài khoảng → không tạo được run.

   Đọc trong task:
     TaskFlow: def f(params=None, dag_run=None)   params["threshold"], dag_run.conf
     Operator cổ điển (template Jinja): "{{ params.threshold }}", "{{ dag_run.conf }}"
   params = giá trị CUỐI (đã gộp); dag_run.conf = đúng cái người trigger gửi (rỗng nếu theo lịch).

2) Rẽ nhánh — @task.branch

   Hàm trả task_id (str) hoặc list task_id của nhánh được chạy; nhánh còn lại → skipped,
   và skipped LAN xuống các task phía dưới nó. Trả None → skip hết.
   EmptyOperator = task rỗng, làm đích cho nhánh "không làm gì" (no_drift của tutorial07).

3) trigger_rule — khi nào task được chạy, tính theo trạng thái các upstream

   all_success (mặc định)          mọi upstream success → sau branch LUÔN bị skip (bẫy)
   none_failed_min_one_success     không có failed + ít nhất 1 success → cách đúng để gộp nhánh
   all_done                        mọi upstream đã xong, bất kể kết quả → dọn dẹp, ghi log
   (còn: one_success, one_failed, all_failed, none_failed, none_skipped, always)

4) "Bỏ qua" khác "lỗi"

   tutorial07: Evidently trả 400 (chưa có reference / chưa đủ mẫu) → task trả status "skipped",
   branch chọn no_drift → run XANH. Hệ thống mới dựng chưa có dữ liệu là bình thường, không nên
   đỏ và không nên kích hoạt on_failure_callback (bài 07).

5) max_active_runs=1

   Tối đa một run của DAG cùng lúc: phân tích drift chồng nhau vừa tốn tài nguyên vừa có thể
   trigger train lại hai lần.

DAG trong bài:
  lesson06_drift_decision   khung drift_monitoring của tutorial07; kết quả Evidently giả lập bằng
                            param simulated_share / simulate_not_ready; thêm task gộp record_decision
  lesson06_trigger_rules    3 task gộp với 3 trigger_rule cạnh nhau; param pick (enum), fail_b

File:
  dags/drift_decision.py
  dags/trigger_rules.py
  data/decisions.jsonl      record_decision ghi mỗi run một dòng (sinh ra khi chạy)

TỔNG KẾT
  - Param = tham số có kiểu + ràng buộc; UI sinh form; conf ghi đè và bị kiểm tra.
  - Trong task: params (giá trị cuối) và dag_run.conf (cái được gửi); trong template: {{ params.x }}.
  - @task.branch trả task_id nhánh được chạy; nhánh còn lại skipped và lan xuống dưới.
  - Task gộp sau branch phải đổi trigger_rule (none_failed_min_one_success), nếu không sẽ bị skip.
  - "Chưa đủ dữ liệu" nên là nhánh xanh (skipped/no_drift), không phải lỗi.
"""
print(__doc__)
