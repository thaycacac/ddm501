"""
BÀI 18 — Bước 2: tutorial02-extend/03_configuration_alias.py, viết lại có comment.

  python step2_aliases.py        như extend: dev=2, staging=2, prod=1, rồi promote dev → staging
  python step2_aliases.py ship   phần extend để comment: promote staging → prod

Bài 19 cần prod=1, dev=2 → sau khi thử "ship", chạy lại lệnh không tham số để đặt lại.
"""
from __future__ import annotations

import sys

from connect import MODEL_NAME, client, show_pg


def configure_alias(model_name: str, alias: str, version: str) -> None:
    # Alias chưa có → tạo. Đã có → DỜI sang version mới (alias cũ không còn trỏ về bản cũ).
    client().set_registered_model_alias(name=model_name, alias=alias, version=version)
    print(f"  set   @{alias:<8} → v{version}")


def promote_model(model_name: str, from_alias: str, to_alias: str) -> str:
    # Promote = hai lệnh: hỏi @from đang trỏ version nào, rồi đặt @to vào đúng version đó.
    version = client().get_model_version_by_alias(name=model_name, alias=from_alias).version
    client().set_registered_model_alias(name=model_name, alias=to_alias, version=version)
    print(f"  promote @{from_alias} (v{version}) → @{to_alias}")
    return version


def show_aliases(title: str) -> None:
    # get_registered_model(...).aliases: dict {alias: version}
    aliases = client().get_registered_model(MODEL_NAME).aliases
    print(f"\n{title}: {dict(sorted(aliases.items()))}")


def main() -> None:
    show_aliases("Alias hiện tại")

    if sys.argv[1:] == ["ship"]:
        print("\nShip staging → prod:")
        promote_model(MODEL_NAME, "staging", "prod")
    else:
        print("\nCấu hình như 03_configuration_alias.py:")
        configure_alias(MODEL_NAME, "dev", "2")
        configure_alias(MODEL_NAME, "staging", "2")
        configure_alias(MODEL_NAME, "prod", "1")
        promote_model(MODEL_NAME, "dev", "staging")

    show_aliases("Alias sau khi chạy")

    print("\nPostgres — registered_model_aliases (alias chỉ là một dòng ở đây):")
    show_pg("SELECT alias, version FROM registered_model_aliases "
            "WHERE name = %s ORDER BY alias", (MODEL_NAME,))


if __name__ == "__main__":
    main()
