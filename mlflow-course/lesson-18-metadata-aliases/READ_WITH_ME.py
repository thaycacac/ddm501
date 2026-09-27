"""
BÀI 18 — Metadata cho version + alias dev/staging/prod
         (= tutorial02-extend/02_update_models.py + 03_configuration_alias.py)

Dùng lại model course-17-classifier (v1, v2) từ bài 17, chạy trên stack bài 16.
Bài này KHÔNG train gì cả — chỉ sửa "giấy tờ" của model trong registry.

1) Metadata của version  (02_update_models.py)
   update_model_version(description=...)   mô tả version (Markdown được)
   set_model_version_tag(key, value)       tag gắn vào VERSION

   Hai loại tag khác nhau, nằm ở hai bảng khác nhau trong Postgres:
     run tag      (bài 17, mlflow.set_tags)  → bảng tags               — gắn vào lần train
     version tag  (bài này)                  → bảng model_version_tags — gắn vào bản đã register
   Sửa version tag được bất cứ lúc nào; run đã xong thì coi như "biên bản" lúc train.

2) Alias  (03_configuration_alias.py)
   Alias = cái tên trỏ tới MỘT version, di chuyển được.

     course-17-classifier
       ├── v1  ← @prod
       └── v2  ← @dev, @staging

   - Một alias chỉ trỏ tới 1 version; set lại = dời alias sang version khác.
   - Một version có thể có nhiều alias.
   - "Promote dev → staging" chỉ là: đọc version của @dev, rồi set @staging vào version đó.
     Không copy file, không train lại — chỉ đổi một dòng trong bảng registered_model_aliases.
   - Code phục vụ gọi models:/NAME@prod (bài 19) → đổi alias là đổi model đang chạy,
     không cần sửa code phục vụ.

   (Bài 09 bạn đã set alias "champion". Bài này thêm: nhiều môi trường + promote.)

File trong bài:
  connect.py              đọc .env bài 16, MODEL_NAME = course-17-classifier, hàm show_pg()
  step1_update_version.py = 02_update_models.py (+ in trước/sau, nhìn vào Postgres)
  step2_aliases.py        = 03_configuration_alias.py (+ in bản đồ alias, tuỳ chọn "ship")
"""
print(__doc__)
