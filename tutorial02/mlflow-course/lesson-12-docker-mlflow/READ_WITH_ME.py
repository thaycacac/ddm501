"""
BÀI 12 — Docker hóa MLflow = ghép bài 01–03 (Docker) + bài 04–06 (server SQLite).

Bạn sẽ đọc file THẬT của Tutorial 02 (không copy lan man):

  ../../ddm501-t02-mlflow/Dockerfile
  ../../ddm501-t02-mlflow/docker-compose.yml

Ánh xạ đã học:

| Bạn đã học          | Trong T02                                      |
|---------------------|------------------------------------------------|
| Image vs container  | build image ddm501-t02-mlflow:2.19.0           |
| Dockerfile CMD      | mlflow server ... --host 0.0.0.0 --port 5000   |
| -p HOST:CONT        | ports "15000:5000" (tránh AirPlay :5000)       |
| Bind mount          | ./mlflow-data:/work/mlflow-data                |
| Healthcheck         | urllib → localhost:5000/health                 |
| profiles + run      | service runner (tools) chạy step1..4           |
| Tên service DNS     | MLFLOW_TRACKING_URI=http://mlflow:5000         |
| down giữ data       | mlflow-data/ vẫn còn sau compose down          |

Sau bài này: Capstone = chạy 4 script Tutorial 02 end-to-end và giải thích được.
"""
print(__doc__)
