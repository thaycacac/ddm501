"""
BÀI 03 — 5 task nối giống hệt tutorial04 (ingest/validate/split/scale/report).

  extract ─► validate ─┬─► stats ──(>>)──► normalize
                       └──────────────────► normalize
  validate, stats, normalize ─► report   (fan-in)

Dữ liệu thật đi qua FILE trong data/staging/lesson03/.
XCom chỉ mang dict nhỏ: số đếm + đường dẫn.
"""
# Cho phép viết type hint kiểu mới (dict, str | None) mà không lỗi ở Python cũ
from __future__ import annotations

import json          # đọc/ghi file .json (dữ liệu trung gian giữa các task)
import logging       # ghi log → hiện trong tab Logs của từng task trên UI
import statistics    # mean / stdev cho task stats
from datetime import datetime   # dùng cho start_date của DAG
from pathlib import Path        # thao tác đường dẫn file gọn hơn os.path

# dag: decorator biến một hàm thành DAG. task: decorator biến một hàm thành task.
from airflow.decorators import dag, task

# Logger riêng của file này. log.info(...) trong task → ghi vào file log của task instance
log = logging.getLogger(__name__)

# Thư mục chứa output của DAG.
#   __file__           = /opt/airflow/dags/xcom_pipeline.py (trong container)
#   .parents[1]        = /opt/airflow
#   → OUT              = /opt/airflow/data/staging/lesson03
# /opt/airflow/data là bind mount của ./data trên máy bạn → mở được file từ máy.
OUT = Path(__file__).resolve().parents[1] / "data" / "staging" / "lesson03"

# "Dữ liệu nguồn" giả lập: 12 con số, trong đó 2 số âm đóng vai "dòng xấu"
# (giống các dòng lỗi trong data/raw/wdbc.csv của tutorial04).
SOURCE = [3, 7, -1, 12, 5, 9, -4, 8, 6, 10, 4, 11]


# ---------------------------------------------------------------------------
# Khai báo DAG: mọi tham số ở đây là "thông tin về pipeline", chưa chạy gì cả
# ---------------------------------------------------------------------------
@dag(
    dag_id="lesson03_xcom",            # tên duy nhất, hiện trên UI và dùng trong CLI
    schedule=None,                     # không có lịch → chỉ chạy khi trigger tay / dags test
    start_date=datetime(2026, 9, 1),   # bắt buộc phải có; với schedule=None gần như không ảnh hưởng
    catchup=False,                     # không chạy bù quá khứ (bài 02)
    tags=["airflow-course", "lesson-03"],  # nhãn để lọc DAG trên UI
)
def lesson03_xcom():
    # Mọi thứ bên trong hàm này chạy LÚC PARSE (scheduler đọc file ~30s/lần):
    #   - định nghĩa các task (các hàm @task bên dưới)
    #   - nối các task với nhau (6 dòng cuối)
    # Code BÊN TRONG từng hàm @task chỉ chạy khi task đó thực sự được chạy.

    # ---------------- Task 1: extract (≈ ingest của tutorial04) ----------------
    @task  # biến hàm thành task; tên task = tên hàm ("extract")
    def extract() -> dict:
        OUT.mkdir(parents=True, exist_ok=True)   # tạo thư mục output nếu chưa có
        path = OUT / "numbers.json"              # file "snapshot" dữ liệu nguồn
        path.write_text(json.dumps(SOURCE))      # ghi 12 con số ra file
        log.info("extracted %d numbers", len(SOURCE))  # → tab Logs của task extract
        # Giá trị return được Airflow lưu vào bảng xcom (key = "return_value").
        # Chỉ trả thứ NHỎ: số dòng + ĐƯỜNG DẪN file. Dữ liệu thật nằm trong file.
        return {"rows": len(SOURCE), "path": str(path)}

    # ---------------- Task 2: validate (≈ validate của tutorial04) -------------
    @task
    def validate(meta: dict) -> dict:
        # meta = dict mà extract đã return. Airflow tự lấy từ XCom và truyền vào
        # vì ở dưới ta viết validate(extracted).
        numbers = json.loads(Path(meta["path"]).read_text())  # đọc file extract đã ghi
        clean = [n for n in numbers if n >= 0]                # bỏ số âm = lọc dòng xấu
        path = OUT / "clean.json"                             # file chứa dữ liệu sạch
        path.write_text(json.dumps(clean))                    # ghi dữ liệu sạch ra file
        log.info("clean=%d rejected=%d", len(clean), len(numbers) - len(clean))
        # Trả về XCom: đường dẫn file sạch + số đếm (report sẽ dùng số đếm này)
        return {"path": str(path), "clean": len(clean), "rejected": len(numbers) - len(clean)}

    # ---------------- Task 3: stats (≈ split của tutorial04) -------------------
    @task
    def stats(meta: dict) -> dict:
        # meta = dict của validate → lấy đường dẫn clean.json
        clean = json.loads(Path(meta["path"]).read_text())
        # Tính trung bình và độ lệch chuẩn của dữ liệu sạch
        result = {"mean": statistics.mean(clean), "std": statistics.stdev(clean)}
        # Ghi ra FILE stats.json để normalize đọc.
        # normalize KHÔNG nhận return của stats → Airflow không tự biết thứ tự
        # → phải viết stats_info >> normalized ở dưới.
        (OUT / "stats.json").write_text(json.dumps(result))
        log.info("stats %s", result)
        # Vẫn return (làm tròn) để report nhận qua XCom
        return {k: round(v, 4) for k, v in result.items()}

    # ---------------- Task 4: normalize (≈ scale của tutorial04) ---------------
    @task
    def normalize(meta: dict) -> dict:
        # meta = dict của validate (KHÔNG phải của stats) → đọc dữ liệu sạch
        clean = json.loads(Path(meta["path"]).read_text())
        # Đọc stats.json do task stats ghi. Nếu stats chưa chạy → FileNotFoundError.
        # Đây là lý do cần dòng  stats_info >> normalized.
        s = json.loads((OUT / "stats.json").read_text())
        # Chuẩn hoá z-score: (x - mean) / std
        scaled = [round((n - s["mean"]) / s["std"], 4) for n in clean]
        (OUT / "normalized.json").write_text(json.dumps(scaled))  # ghi kết quả ra file
        log.info("normalized %d numbers", len(scaled))
        return {"normalized": len(scaled)}   # XCom: chỉ số lượng, không trả cả list

    # ---------------- Task 5: report (≈ report của tutorial04) -----------------
    @task
    def report(validation: dict, stats_info: dict, norm_info: dict) -> str:
        # Fan-in: nhận 3 input → Airflow chờ CẢ 3 task (validate, stats, normalize)
        # thành công rồi mới chạy report.
        summary = {**validation, **stats_info, **norm_info}  # gộp 3 dict thành 1
        summary.pop("path", None)            # bỏ đường dẫn, báo cáo chỉ cần con số
        line = json.dumps(summary, sort_keys=True)  # 1 dòng JSON, key sắp xếp cố định
        log.info("summary: %s", line)
        return line                          # XCom của report = chuỗi tóm tắt

    # ---------------------------------------------------------------------------
    # Nối task: CHỈ VẼ ĐỒ THỊ, chưa chạy task nào.
    # Gọi extract() ở đây không chạy hàm extract — nó trả về một XComArg
    # ("lời hứa": sau này sẽ có giá trị return của extract).
    # Cùng hình với tutorial04 dòng 160–165.
    # ---------------------------------------------------------------------------
    extracted = extract()                  # tạo task extract; extracted = XComArg
    validated = validate(extracted)        # truyền XComArg → tự sinh cạnh extract → validate
    stats_info = stats(validated)          # tự sinh cạnh validate → stats
    normalized = normalize(validated)      # tự sinh cạnh validate → normalize
    stats_info >> normalized               # TỰ VIẾT cạnh stats → normalize (vì truyền qua file)
    report(validated, stats_info, normalized)  # 3 cạnh vào report: validate, stats, normalize


# Gọi hàm DAG ở cấp module để tạo đối tượng DAG.
# Scheduler chỉ nhận ra DAG khi đối tượng này tồn tại lúc import file.
lesson03_xcom()
