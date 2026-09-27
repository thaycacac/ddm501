"""
BÀI 14 — MinIO: kho file kiểu S3 tự host (CHƯA có MLflow trong bài này)

Vấn đề còn lại sau bài 13:
  Metadata đã lên Postgres (server riêng, nhiều máy dùng chung được),
  nhưng FILE vẫn nằm ở ./mlartifacts trên MỘT máy:
    - máy khác / container khác không đọc được
    - đĩa máy đó hỏng → mất model
  → cần một "kho file" chạy như service riêng, ai có địa chỉ + key đều dùng được.

Object storage (S3) — 3 khái niệm:

  bucket   cái thùng, tên duy nhất              vd: mlflow
  key      "tên" đầy đủ của object trong thùng  vd: artifacts/1/<run_id>/artifacts/notes.txt
  object   nội dung file + metadata

  Không có thư mục thật! "artifacts/1/" chỉ là PHẦN ĐẦU (prefix) của key.
  Console/UI vẽ nó thành thư mục cho dễ nhìn.

  Địa chỉ đầy đủ viết dạng:  s3://<bucket>/<key>
  → Nhớ artifact_uri ở bài 13 (mlflow-artifacts:/1/...)? Bài 15 nó sẽ thành s3://mlflow/...

S3 API vs AWS S3 vs MinIO:
  - S3 API  = "ngôn ngữ" (HTTP) để nói chuyện với kho file — gần như chuẩn chung
  - AWS S3  = dịch vụ của Amazon, nói ngôn ngữ đó
  - MinIO   = phần mềm bạn tự chạy (Docker), CŨNG nói ngôn ngữ đó
  - boto3   = thư viện Python nói S3. Nó không biết đầu bên kia là AWS hay MinIO;
              chỉ đi tới endpoint_url bạn chỉ. Không chỉ → mặc định đi AWS thật.
  Vì vậy key của MinIO vẫn mang tên AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY.

MinIO mở 2 port:
  9000  API     — boto3 / MLflow / mc nói chuyện ở đây
  9001  Console — giao diện web cho NGƯỜI

Ánh xạ vào tutorial02-extend/docker-compose.yml:
  dòng 27–46   service minio       ↔ service minio của bài này
  dòng 95–111  service minio-init  ↔ service minio-init của bài này (bước 3)

File trong bài:
  docker-compose.yml      minio + minio-init
  connect.py              WHERE = endpoint MinIO + key; hàm s3_client()
  step1_boto3_basics.py   tạo bucket, upload, list, download bằng boto3
  step2_break_it.py       sai key / thiếu endpoint / MinIO tắt → đọc lỗi

Thứ tự học: làm theo hướng dẫn trong chat, từng bước một.
"""
print(__doc__)
