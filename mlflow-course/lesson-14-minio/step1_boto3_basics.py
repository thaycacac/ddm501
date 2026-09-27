"""
BÀI 14 — Bước 2: nói chuyện với MinIO bằng code (boto3), không qua trình duyệt.

Đây chính là việc MLflow client sẽ làm ở bài 15 khi bạn gọi log_artifact:
  tạo đường dẫn key  →  upload object  →  (sau này) list / download lại.

Script làm lần lượt 6 việc, mỗi việc 1 API S3:
  1. list_buckets       có những thùng nào
  2. create_bucket      tạo thùng course-14 (nếu chưa có)
  3. put_object         ghi một object từ chuỗi trong RAM
  4. upload_file        upload một file trên đĩa, key có dấu "/"
  5. list_objects_v2    liệt kê object (và "thư mục" = prefix)
  6. get_object         đọc lại nội dung
"""
from __future__ import annotations

from pathlib import Path

from connect import BUCKET, s3_client

TMP = Path(__file__).resolve().parent / "_tmp"
TMP.mkdir(exist_ok=True)


def main() -> None:
    s3 = s3_client()

    # --- 1. list_buckets --------------------------------------------------
    buckets = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    print(f"\n1. buckets hiện có      = {buckets}")

    # --- 2. create_bucket -------------------------------------------------
    # Tạo bucket đã tồn tại sẽ lỗi (BucketAlreadyOwnedByYou) → kiểm tra trước.
    # minio-init (bước 3) làm đúng việc này bằng `mc mb --ignore-existing`.
    if BUCKET not in buckets:
        s3.create_bucket(Bucket=BUCKET)
        print(f"2. đã tạo bucket         {BUCKET}")
    else:
        print(f"2. bucket đã có sẵn      {BUCKET}")

    # --- 3. put_object: nội dung lấy thẳng từ bytes ------------------------
    s3.put_object(Bucket=BUCKET, Key="hello.txt", Body=b"xin chao minio\n")
    print(f"3. put_object            s3://{BUCKET}/hello.txt")

    # --- 4. upload_file: file trên đĩa, key có nhiều "/" -----------------
    # Key này bắt chước đường dẫn artifact của MLflow: <exp>/<run>/artifacts/<file>
    # Không cần "tạo thư mục" trước — trong S3 không có thư mục thật.
    note = TMP / "notes.txt"
    note.write_text("đây là file giả làm artifact của một run\n", encoding="utf-8")
    key = "artifacts/1/run-001/artifacts/notes.txt"
    s3.upload_file(str(note), BUCKET, key)
    print(f"4. upload_file           s3://{BUCKET}/{key}")

    # --- 5a. list_objects_v2: tất cả object trong bucket -------------------
    print(f"\n5a. mọi object trong {BUCKET}:")
    for obj in s3.list_objects_v2(Bucket=BUCKET).get("Contents", []):
        print(f"    {obj['Key']:<45} {obj['Size']:>4} bytes")

    # --- 5b. Prefix + Delimiter: cách console "vẽ" ra thư mục -------------
    # Delimiter="/" → gom các key có cùng đoạn tiếp theo thành CommonPrefixes
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="artifacts/", Delimiter="/")
    folders = [p["Prefix"] for p in resp.get("CommonPrefixes", [])]
    print(f"5b. 'thư mục' dưới artifacts/ = {folders}")

    # --- 6. get_object: đọc lại -------------------------------------------
    body = s3.get_object(Bucket=BUCKET, Key="hello.txt")["Body"].read().decode()
    print(f"\n6. nội dung hello.txt    = {body!r}")

    print("\nConsole: http://127.0.0.1:29001 → Object Browser → course-14")


if __name__ == "__main__":
    main()
