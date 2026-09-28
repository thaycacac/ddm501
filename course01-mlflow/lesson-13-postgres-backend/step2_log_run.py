"""
BÀI 13 — Bước 2: log MỘT run, rồi tự đi tìm từng mảnh dữ liệu của nó.

  param / metric / tag ──HTTP──▶ MLflow server ──SQL──▶ Postgres       (metadata)
  file notes.txt       ──HTTP──▶ MLflow server ──────▶ ./mlartifacts  (đĩa máy bạn)

Script sẽ:
  1. log 1 param, 1 metric, 1 tag, 1 file
  2. SELECT thẳng trong Postgres → thấy param/metric/tag, và ĐỊA CHỈ của file
  3. tìm file thật trong ./mlartifacts

Cần: Postgres (docker compose) và `mlflow server` (bước 3) đang chạy.
"""
from __future__ import annotations

from pathlib import Path

import mlflow
import psycopg2
from mlflow.exceptions import MlflowException

from connect import EXPERIMENT, PG, TRACKING_URI, connect

LESSON_DIR = Path(__file__).resolve().parent
TMP = LESSON_DIR / "_tmp"
TMP.mkdir(exist_ok=True)


def log_one_run() -> mlflow.entities.Run:
    # Script chỉ biết MLflow server (connect.py). Nó KHÔNG biết Postgres tồn tại.
    connect()
    with mlflow.start_run(run_name="hello-postgres") as run:
        mlflow.set_tag("lesson", "13")           # → bảng tags
        mlflow.log_param("backend", "postgres")  # → bảng params
        mlflow.log_metric("answer", 42.0)        # → bảng metrics

        note = TMP / "notes.txt"
        note.write_text(f"run_id={run.info.run_id}\n", encoding="utf-8")
        mlflow.log_artifact(str(note))           # → file, KHÔNG vào Postgres
    return mlflow.get_run(run.info.run_id)


def show_in_postgres(run_id: str) -> None:
    # Cột id của run trong schema tên là run_uuid (tên lịch sử của MLflow).
    with psycopg2.connect(**PG) as conn, conn.cursor() as cur:
        cur.execute("SELECT key, value FROM params WHERE run_uuid = %s", (run_id,))
        params = cur.fetchall()
        cur.execute("SELECT key, value FROM metrics WHERE run_uuid = %s", (run_id,))
        metrics = cur.fetchall()
        cur.execute("SELECT key, value FROM tags WHERE run_uuid = %s AND key = 'lesson'",
                    (run_id,))
        tags = cur.fetchall()
        cur.execute("SELECT status, artifact_uri FROM runs WHERE run_uuid = %s", (run_id,))
        status, artifact_uri = cur.fetchone()
    conn.close()
    print(f"\n[Postgres] runs.status       = {status}")
    print(f"[Postgres] params            = {params}")
    print(f"[Postgres] metrics           = {metrics}")
    print(f"[Postgres] tags (lesson)     = {tags}")
    # Postgres KHÔNG chứa nội dung file — chỉ chứa ĐỊA CHỈ của thư mục file
    print(f"[Postgres] runs.artifact_uri = {artifact_uri}")


def show_on_disk(run_id: str) -> None:
    # artifact_uri dạng mlflow-artifacts:/<exp_id>/<run_id>/artifacts nghĩa là
    # "hỏi server"; server map nó vào ./mlartifacts/<exp_id>/<run_id>/artifacts
    # trong thư mục mà bạn đứng lúc bật server.
    base = LESSON_DIR / "mlartifacts"
    files = [p for p in base.glob(f"*/{run_id}/artifacts/**/*") if p.is_file()]
    print()
    if not files:
        print(f"[đĩa] không thấy file dưới {base} — lúc bật `mlflow server` "
              "bạn có đứng trong thư mục bài 13 không?")
    for path in files:
        print(f"[đĩa] {path.relative_to(LESSON_DIR)}  ({path.stat().st_size} bytes)")


def main() -> None:
    try:
        run = log_one_run()
    except MlflowException as exc:
        msg = str(exc)
        # Hai kiểu hỏng khác nhau hoàn toàn, dù cùng một exception:
        if "Connection refused" in msg:
            print("LỖI: không ai nghe ở", TRACKING_URI, "→ MLflow server chưa chạy.")
        elif "500" in msg:
            print("LỖI 500: server CÓ chạy nhưng hỏng ở phía sau "
                  "(Postgres?) → xem log ở terminal đang chạy mlflow server.")
        else:
            print("LỖI:", msg[:300])
        return
    run_id = run.info.run_id
    print(f"run_id       = {run_id}")
    print(f"artifact_uri = {run.info.artifact_uri}")

    show_in_postgres(run_id)
    show_on_disk(run_id)

    print(f"\nUI: {TRACKING_URI} → experiment '{EXPERIMENT}' → run 'hello-postgres'")


if __name__ == "__main__":
    main()
