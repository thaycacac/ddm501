"""
BÀI 18 — Bước 1: tutorial02-extend/02_update_models.py, viết lại có comment.

Gắn description + tag cho version 2, rồi nhìn xem chúng nằm đâu trong Postgres.
Chạy lại nhiều lần vẫn cho cùng kết quả (update = ghi đè, không tạo version mới).
"""
from __future__ import annotations

from connect import MODEL_NAME, client, show_pg

VERSION = "2"  # extend cũng hardcode "2": bản mới hơn sau một lần chạy 01_training.py

# Description nói "500" — khớp model thật (bài 17), dù run v2 của extend lại ghi param 200.
DESCRIPTION = """
Trained on the breast cancer dataset (Wisconsin Diagnostic).
- Algorithm: Random Forest
- n_estimators: 500
- random_state: 42
"""


def main() -> None:
    c = client()

    before = c.get_model_version(MODEL_NAME, VERSION)
    print(f"TRƯỚC  description={before.description!r}  tags={before.tags}")

    # update_model_version: hiện chỉ sửa được description
    c.update_model_version(name=MODEL_NAME, version=VERSION, description=DESCRIPTION)

    # set_model_version_tag: thêm/ghi đè MỘT tag của version (không phải run tag)
    c.set_model_version_tag(name=MODEL_NAME, version=VERSION,
                            key="algorithm", value="random_forest")

    after = c.get_model_version(MODEL_NAME, VERSION)
    print(f"SAU    description={after.description.strip()[:40]!r}...  tags={after.tags}")

    print("\nPostgres — model_versions (description nằm ở đây):")
    show_pg("SELECT version, left(description, 40) FROM model_versions "
            "WHERE name = %s ORDER BY version", (MODEL_NAME,))

    print("\nPostgres — model_version_tags (tag của VERSION):")
    show_pg("SELECT version, key, value FROM model_version_tags WHERE name = %s", (MODEL_NAME,))

    print("\nPostgres — tags (tag của RUN sinh ra v2, đặt ở bài 17 — không đổi):")
    show_pg("SELECT key, value FROM tags WHERE run_uuid = %s "
            "AND key NOT LIKE 'mlflow.%%' ORDER BY key", (after.run_id,))

    print(f"\nUI → Models → {MODEL_NAME} → Version {VERSION}")


if __name__ == "__main__":
    main()
