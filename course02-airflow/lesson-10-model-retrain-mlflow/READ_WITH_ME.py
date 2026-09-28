"""
BÀI 10 — DAG train lại có quality gate, chạy thật với MLflow + API
         (= tutorial07/airflow_dags/model_retrain.py, tutorial07/scripts/training.py,
            tutorial07/airflow/Dockerfile + requirements.txt, POST /model/reload trong tutorial07/api/main.py)

1) Kiến trúc (hai project compose, một mạng)

   course01 bài 16 (mlflow-course-16-net):  postgres ── mlflow:5000 ── minio:9000
                                               ▲             ▲              ▲
   bài này (networks external):     airflow-init/webserver/scheduler     api:8000
   - Airflow dùng CHUNG Postgres với MLflow (database "airflow"), đúng như tutorial07.
   - networks.external: nối vào mạng có sẵn; `docker compose down` bài này không xóa mạng đó.
   - Không depends_on được service của project khác → phải bật stack MLflow TRƯỚC.

2) Image Airflow cho DAG train
   - pip install "apache-airflow==<version đang dùng>" cùng lệnh với thư viện thêm → pip không được
     đổi version Airflow.
   - mlflow-skinny (chỉ client), cùng version với server.
   - scikit-learn + python phải TRÙNG giữa nơi train (Airflow) và nơi load (API): model là file pickle.

3) Luồng model_retrain
   train_model     import training LÚC CHẠY (parse DAG nhanh, MLflow sập không làm Broken DAG);
                   log_model(registered_model_name) → mỗi lần chạy thêm 1 version; tag airflow_run_id.
   quality_gate    accuracy < min_accuracy → AirflowFailException (đỏ, callback, không retry)
                   (bổ sung) require_better và kém champion → AirflowSkipException (xanh, bỏ qua promote)
   promote_model   stage Production + archive bản cũ (tutorial07); alias champion (cách mới)
   reload_api      POST /model/reload; (bổ sung) kiểm tra API phục vụ đúng version vừa promote
   notify_success  Telegram: version, 4 metric, link MLflow run

   Fail và Skip khác nhau:
     AirflowFailException  lỗi thật, cần người xem           → failed + on_failure_callback
     AirflowSkipException  kết quả bình thường, không làm tiếp → skipped, task sau skipped, run success

4) Những điểm của tutorial07 cần biết khi đọc (sẽ gặp lại ở Capstone)
   - Retrain dùng lại dataset TĨNH (load_wine, random_state=42) → mọi lần retrain cho CÙNG accuracy;
     "train lại khi drift" không học gì từ dữ liệu production mới.
   - Model train trên load_wine (13 feature, 3 lớp), còn Evidently/giả lập drift dùng Wine Quality
     (11 feature) → hai thế giới dữ liệu không khớp nhau.
   - Gate chỉ so ngưỡng tuyệt đối, không so với bản Production (challenger vs champion).
   - reload_api không kiểm tra version API trả về.
   - API dùng async def cho việc load model → chặn event loop trong lúc reload.
   - Stage (Production/Staging) deprecated từ MLflow 2.9 → log có cảnh báo; alias là cách thay thế.
   - train_model retries=1: nếu lỗi SAU khi đã đăng ký version, lần retry sinh thêm version thừa.

File:
  airflow/Dockerfile        airflow-course:2.8.4 + mlflow-skinny 2.19.0 + scikit-learn 1.5.2
  scripts/training.py       train_and_register / get_production / promote_to_production
  dags/model_retrain.py     lesson10_model_retrain
  dags/utils/               common.py (URL, DEFAULT_ARGS), telegram_alert.py (chép bài 07)
  api/                      FastAPI load models:/wine_quality_model/Production, /model/reload
  scripts/api_client.py     health / info / predict / reload từ máy

TỔNG KẾT
  - Hai project compose nói chuyện qua mạng external; bật stack sở hữu mạng + DB trước.
  - Image Airflow thêm thư viện: ghim apache-airflow trong cùng lệnh pip; dùng mlflow-skinny;
    sklearn/python trùng với phía API.
  - DAG import thư viện nặng bên trong task, không ở đầu file.
  - Luôn đăng ký version, chỉ promote khi qua gate; Fail = lỗi cần người, Skip = không làm tiếp nhưng xanh.
  - Sau promote phải reload serving và KIỂM TRA version thực sự đang phục vụ.
"""
print(__doc__)
