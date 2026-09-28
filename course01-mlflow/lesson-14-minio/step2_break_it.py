"""
BÀI 14 — Bước 4: cố ý làm sai từng thứ trong 3 thứ boto3 cần, rồi đọc lỗi.

  python step2_break_it.py wrong-secret   sai mật khẩu
  python step2_break_it.py wrong-key      sai access key (user không tồn tại)
  python step2_break_it.py no-endpoint    quên endpoint → boto3 đi AWS S3 thật
  python step2_break_it.py ok             đúng hết (để so sánh / sau khi tắt MinIO)

Bài 15 MLflow cũng dùng boto3 bên dưới → gặp đúng các lỗi này khi cấu hình sai.
"""
from __future__ import annotations

import argparse

from botocore.exceptions import ClientError

from connect import s3_client

CASES = {
    "ok": {},
    "wrong-secret": {"secret_key": "sai-mat-khau"},
    "wrong-key": {"access_key": "khong-ton-tai"},
    "no-endpoint": {"endpoint": None},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=CASES)
    args = ap.parse_args()

    s3 = s3_client(**CASES[args.case])
    try:
        names = [b["Name"] for b in s3.list_buckets()["Buckets"]]
        print(f"\nOK   buckets = {names}")
    except ClientError as exc:
        # Server CÓ trả lời, nhưng từ chối. Mã lỗi nằm trong response.
        err = exc.response["Error"]
        print(f"\nClientError  code = {err['Code']}")
        print(f"             msg  = {err['Message']}")
    except Exception as exc:
        # Không nói chuyện được với server nào cả (vd: không ai nghe ở port đó)
        print(f"\n{type(exc).__name__}: {str(exc)[:200]}")


if __name__ == "__main__":
    main()
