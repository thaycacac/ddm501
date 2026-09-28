"""
BÀI 09 — Metric của Airflow: StatsD → statsd-exporter → Prometheus
         (= tutorial07/docker-compose.yml dòng 18–21 và 351–362, tutorial07/config/statsd_mapping.yml,
            job "airflow" trong tutorial07/config/prometheus.yml, nhóm airflow_alerts trong
            tutorial07/config/grafana/alerts.yml)

1) Đường đi của metric

   scheduler / task ──UDP 9125 (StatsD, PUSH)──► statsd-exporter ──:9102/metrics (PULL)──► Prometheus
   Airflow 2.x không có /metrics → không scrape thẳng được. statsd-exporter nhận push, giữ trong RAM,
   phơi ra cho Prometheus kéo. Metric chủ yếu phát ra từ container SCHEDULER (nơi task chạy, bài 08).

   Bật bằng 4 biến: AIRFLOW__METRICS__STATSD_ON / _HOST / _PORT / _PREFIX.
   UDP không có xác nhận: sai host, exporter chưa lên → metric mất, Airflow KHÔNG báo lỗi.

2) Giao thức StatsD: "<tên>:<giá trị>|<loại>"
   |c counter   |g gauge   |ms timer (mili-giây)
   Airflow nhét dag_id/task_id vào tên: airflow.ti.finish.<dag_id>.<task_id>.<state>:1|c

3) Mapping — biến đoạn trong tên thành label
   - match: "airflow.ti.finish.*.*.*"      "*" = đúng một đoạn giữa hai dấu chấm
     name: "airflow_task_finish_total"
     labels: {dag_id: "$1", task_id: "$2", state: "$3"}
   Luật đầu tiên khớp thắng. Không khớp luật nào → vẫn xuất, tên thay "." thành "_", không label.
   Timer → giây, dạng summary: _sum, _count, {quantile="0.5|0.9|0.99"}.
   Counter cộng dồn trong exporter; exporter restart → về 0 → luôn dùng rate()/increase().

4) Metric tutorial07 dùng (Airflow bắn → tên Prometheus sau mapping)
   dagrun.duration.<success|failed>.<dag>  airflow_dagrun_duration_<success|failed>_seconds_{sum,count}
   dag.<dag>.<task>.duration               airflow_task_duration_seconds{dag_id,task_id}
   ti.finish.<dag>.<task>.<state>          airflow_task_finish_total{dag_id,task_id,state}
   ti.start.<dag>.<task>                   airflow_task_start_total
   ti_failures / ti_successes              airflow_task_failures_total / _successes_total
   scheduler_heartbeat                     airflow_scheduler_heartbeat_total
   dag_processing.import_errors            airflow_dag_import_errors
   (bài thêm) executor.running_tasks...    airflow_executor_running_tasks / queued_tasks / open_slots

5) Rule Airflow của tutorial07
   AirflowDAGFailed   increase(..._failed_seconds_count[1h]) > 3, for 5m
                      chạy được nhưng: fail 1–3 lần/giờ không báo; lần fail ĐẦU TIÊN của mỗi dag_id
                      không được đếm (increase cần 2 mẫu, series sinh ra đã = 1); $value là số lẻ.
   AirflowTaskStuck   airflow_task_instance_duration_seconds > 3600 → metric KHÔNG TỒN TẠI → không
                      bao giờ fire. StatsD chỉ bắn thời lượng task khi task ĐÃ XONG → không đo được
                      task đang treo. Cách đúng: execution_timeout trên task (kill → failed → alert/callback).
   Thiếu              scheduler chết: up{job="airflow"} vẫn = 1 (exporter còn sống, trả số cũ) →
                      phải bắt "heartbeat ngừng tăng": rate(airflow_scheduler_heartbeat_total[1m]) == 0.
                      DAG lỗi import: airflow_dag_import_errors > 0.

   Mẫu PromQL bắt cả series mới:
     increase(X[10m]) > 0  or  (X unless X offset 10m)

File:
  statsd/statsd_mapping.yml   phần 1 = tutorial07, phần 2 = executor gauges
  prometheus/rules/airflow.yml  nhóm tutorial07 (nguyên bản) + nhóm course (đã sửa)
  dags/metrics_demo.py        chạy mỗi 2 phút; param fail / seconds (execution_timeout 60s)
  extras/broken_dag.py        copy vào dags/ để tạo lỗi import
  scripts/statsd_lab.py       send: bắn StatsD giả; show: đọc /metrics của exporter

TỔNG KẾT
  - Airflow PUSH StatsD qua UDP → statsd-exporter → Prometheus PULL /metrics. Sai host = mất im lặng.
  - Mapping chuyển dag_id/task_id/state từ TÊN sang LABEL; timer thành summary tính bằng giây.
  - Counter đọc bằng rate/increase; increase bỏ sót lần đầu của series mới → thêm vế "unless offset".
  - up{job="airflow"} chỉ nói exporter sống; scheduler sống phải xem heartbeat còn tăng.
  - Không có metric "task đang chạy bao lâu" → dùng execution_timeout. AirflowTaskStuck của tutorial07
    trỏ vào metric không tồn tại.
"""
print(__doc__)
