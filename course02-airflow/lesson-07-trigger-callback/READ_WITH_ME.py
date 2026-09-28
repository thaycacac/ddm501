"""
BÀI 07 — DAG gọi DAG, callback khi lỗi, util Telegram
         (= tutorial07/airflow_dags/: drift_monitoring.py dòng 79–104, model_retrain.py,
            service_health_check.py, utils/common.py, utils/telegram_alert.py, .airflowignore)

1) Tổ chức code dùng chung

   dags/
     .airflowignore          "utils/" → scheduler không quét thư mục này tìm DAG
     utils/common.py         DEFAULT_ARGS, START_DATE, URL/ngưỡng đọc từ env
     utils/telegram_alert.py send_telegram_message, escape, task_failure_alert
     drift_monitoring.py ... from utils.common import DEFAULT_ARGS
   Airflow tự thêm dags/ vào sys.path nên `from utils...` import được.

2) TriggerDagRunOperator — DAG này tạo run cho DAG khác

   TriggerDagRunOperator(task_id=..., trigger_dag_id="model_retrain",
                         conf={"reason": "drift_monitoring run {{ run_id }}"},
                         wait_for_completion=False)
   - conf sang bên kia thành dag_run.conf và GHI ĐÈ params trùng tên; là template, render ra STRING
     (truyền số qua đây mà bên kia khai Param type="number" → run bị từ chối).
   - wait_for_completion=False: tạo xong run là success (tutorial07). True: chờ run đích xong,
     đích fail → task này fail.
   - DAG đích PAUSED → run đích nằm "queued", không chạy. DAG đích max_active_runs=1 → các run xếp hàng.
   - UI: task trigger có nút "Triggered DAG" nhảy sang run đích; run đích có run_type=manual.
   Tách 2 DAG thay vì gộp 1: retrain chạy tay được riêng, lịch riêng, lịch sử riêng, lỗi retrain
   không làm đỏ DAG giám sát.

3) Callback

   Mức task (tutorial07 dùng, qua default_args):
     on_failure_callback  fail HẲN (hết retry, hoặc AirflowFailException)
     on_retry_callback    mỗi lần fail còn retry
     on_success_callback  task success
   Mức DAG (tham số của DAG(...)): on_failure_callback / on_success_callback gọi 1 lần cho cả run.
   Hàm nhận `context`: task_instance, dag_run, logical_date, exception, params...
   Callback phải tự bắt mọi exception (lỗi trong callback chỉ bị log, tin báo mất).
   Log của callback nằm cuối log của task fail.

   Tránh tin trùng: task tự gửi tin rồi raise (report của health check) → @task(on_failure_callback=None).
   Tránh spam: check_service không raise mà trả healthy=False, report gom lại gửi 1 tin.

4) Util Telegram best effort

   - Thiếu token/chat_id, lỗi mạng, Telegram 400 → log cảnh báo, trả False, KHÔNG raise.
     Báo động hỏng không được làm hỏng pipeline.
   - Không log exception của requests: message chứa URL, URL chứa token.
   - parse_mode=HTML → mọi giá trị động phải escape(); tin > 4096 ký tự → cắt.
   - AIRFLOW__WEBSERVER__BASE_URL phải là địa chỉ nhìn từ máy bạn, nếu không link "Xem log" sai.

5) Retry vs fail ngay (nối bài 05), áp vào tutorial07

   Evidently 5xx / mất mạng       exception thường → retry 1 lần → fail → callback
   Evidently 400 chưa đủ dữ liệu  return "skipped" → xanh, không callback
   Quality gate không đạt         AirflowFailException → không retry → callback
   Service down trong health check trả dữ liệu, report gửi 1 tin, raise với callback=None

   Airflow 2.8 có thể in "Try" lệch 1 trong tin báo lỗi (vd 3/2) do cách đếm try_number cũ;
   tutorial07 dùng 2.10 đã đổi cách đếm.

DAG trong bài (Evidently / MLflow / API vẫn giả lập; ghép thật ở bài 10 và Capstone):
  lesson07_drift_monitoring       share > threshold → Telegram + trigger lesson07_model_retrain
  lesson07_model_retrain          train → quality_gate → promote → reload_api → Telegram
  lesson07_service_health_check   airflow (up) + evidently (down) → 1 tin tổng hợp, run đỏ
File sinh ra: data/registry.json (các version "đã đăng ký" và version production)

TỔNG KẾT
  - Code dùng chung để trong dags/utils/, thêm "utils/" vào .airflowignore.
  - TriggerDagRunOperator tạo run cho DAG khác; conf → dag_run.conf bên kia (string);
    DAG đích phải unpause; wait_for_completion quyết định có chờ hay không.
  - on_failure_callback đặt trong default_args → mọi task fail hẳn đều báo Telegram;
    retry không kích hoạt nó; task tự báo thì tắt bằng on_failure_callback=None.
  - Gửi Telegram là best effort: không raise, không lộ token, escape HTML.
  - Chọn đúng loại kết thúc: retry (tạm thời), fail ngay (vĩnh viễn), skipped/xanh (chưa có dữ liệu).
"""
print(__doc__)
