"""
BÀI 03 — TaskFlow @task + XCom
         (= tutorial04 wdbc_pipeline.py dòng 54–69 và 160–165)

1) Task nói chuyện với nhau bằng 2 đường

   a) XCom (cross-communication): giá trị RETURN của một @task được lưu vào
      bảng "xcom" trong metadata DB. Task sau nhận nó qua tham số.
      → Chỉ để thứ NHỎ: số đếm, đường dẫn, dict vài key.
        DataFrame / model / file lớn KHÔNG đi qua XCom (DB phình, chậm, có giới hạn).
   b) File: task ghi file (data/staging/...), task sau đọc lại.
      → Dữ liệu thật đi đường này; XCom chỉ mang ĐƯỜNG DẪN tới file.

   Tutorial04, dòng 67–69:
       # Returned dicts travel as XCom, which is stored in the metadata database.
       # Keep them to counts and paths -- never a DataFrame.

2) Viết task(...) trong thân DAG KHÔNG chạy task

   extracted = extract()          # lúc parse: extracted là XComArg (một "lời hứa")
   validated = validate(extracted)

   Airflow đọc các dòng này để VẼ ĐỒ THỊ: validate nhận output của extract
   → tự thêm cạnh extract → validate. Giá trị thật chỉ có khi task chạy.

3) Khi nào phải tự viết >>

   Phụ thuộc chỉ tự sinh khi TRUYỀN GIÁ TRỊ. Nếu task B đọc FILE do task A ghi
   nhưng không nhận return của A → Airflow không biết B cần A → có thể chạy B
   trước A → FileNotFoundError. Phải nói rõ:  a_result >> b_result

   Tutorial04 dòng 162–164:
       split_info = split(validated)
       scaling    = scale(validated)   # scale đọc file *_unscaled.parquet do split ghi
       split_info >> scaling           # ...nên phải chờ split

4) Fan-in: một task nhận nhiều input → chờ TẤT CẢ xong
       report(validated, split_info, scaling)      (tutorial04 dòng 165)

DAG của bài (dữ liệu là 12 con số, cố ý có số âm):

   extract ─► validate ─┬─► stats ─────┐
                        │     │ (>>)    │
                        │     ▼         ▼
                        ├─► normalize ─► report
                        └──────────────►

   stats ghi stats.json; normalize ĐỌC stats.json nhưng không nhận return của
   stats → cần  stats_info >> normalized  (giống split >> scale).

File trong bài:
  docker-compose.yml       như bài 02 + mount ./scripts
  dags/xcom_pipeline.py    DAG 5 task ở trên
  scripts/show_xcom.py     đọc thẳng bảng xcom trong SQLite (chạy trong container)
"""
print(__doc__)
