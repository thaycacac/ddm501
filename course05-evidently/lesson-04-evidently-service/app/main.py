"""
Evidently service của khóa — cùng API với tutorial07/evidently/main.py (simulations và DAG
drift_monitoring của tutorial07 gọi được y hệt), nhưng sửa những gì bài 02–03 tìm ra:

  1. drift từng cột đọc từ DataDriftTable (tutorial07 đọc nhầm DatasetDriftMetric → luôn rỗng)
  2. `threshold` trong /analyze thật sự được dùng (= drift_share của DataDriftPreset)
  3. evidently_drift_score luôn = share_of_drifted_columns (tutorial07 ép về 0 khi chưa drift)
  4. evidently_missing_values_ratio được set (tutorial07 khai báo mà không bao giờ set)
  5. biến môi trường thật sự được đọc; có gauge thời điểm phân tích cuối cho alert "lâu không chạy"
  6. /analyze là hàm `def` (chạy trong threadpool) → không chặn event loop, /metrics vẫn trả lời
"""
import json
import logging
import os
import threading
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("evidently-service")

# ---------------------------------------------------------------- cấu hình (đọc env THẬT)
DATA_ROOT = Path(os.getenv("EVIDENTLY_DATA_ROOT", "/app"))
REPORTS_DIR = DATA_ROOT / "reports"
REFERENCE_DIR = DATA_ROOT / "reference"
for d in (REPORTS_DIR, REFERENCE_DIR):
    d.mkdir(parents=True, exist_ok=True)

MIN_SAMPLES = int(os.getenv("EVIDENTLY_MIN_SAMPLES", "100"))        # ít hơn → 400, không phân tích
DEFAULT_WINDOW = int(os.getenv("EVIDENTLY_DEFAULT_WINDOW", "100"))  # số mẫu gần nhất đem so
DEFAULT_DRIFT_SHARE = float(os.getenv("EVIDENTLY_DRIFT_SHARE", "0.5"))
KEEP_REPORTS = int(os.getenv("EVIDENTLY_KEEP_REPORTS", "20"))       # xoay vòng HTML, tránh đầy đĩa
BUFFER_MAX = 10000
# cột metadata do /capture thêm vào — không phải feature, không đem kiểm định drift
EXCLUDE_COLS = {"prediction", "timestamp", "model_version"}

# ---------------------------------------------------------------- metric Prometheus
# Giữ nguyên TÊN của tutorial07 để alert rule và dashboard dùng lại được.
DRIFT_DETECTED = Gauge("evidently_data_drift_detected", "1 nếu dataset drift ở lần phân tích cuối")
DRIFT_SCORE = Gauge("evidently_drift_score", "share_of_drifted_columns ở lần phân tích cuối (0..1)")
DRIFTED_FEATURES_COUNT = Gauge("evidently_drifted_features_count", "Số feature drift ở lần phân tích cuối")
FEATURE_DRIFT = Gauge("evidently_feature_drift", "1 nếu feature drift", ["feature_name"])
MISSING_VALUES = Gauge("evidently_missing_values_ratio", "Tỷ lệ missing của feature trong current",
                       ["feature_name"])
ANALYSIS_COUNT = Counter("evidently_analysis_total", "Số lần phân tích thành công")
ANALYSIS_DURATION = Histogram("evidently_analysis_duration_seconds", "Thời gian một lần phân tích",
                              buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0])
# --- metric MỚI (tutorial07 không có) ---
# Giá trị thô của kiểm định: p-value (KS, chi-square) HOẶC khoảng cách (Wasserstein, JS).
# Label stattest cho biết phải đọc chiều nào (bài 01). Số giá trị label nhỏ, không lo cardinality.
FEATURE_DRIFT_SCORE = Gauge("evidently_feature_drift_score", "drift_score thô của từng feature",
                            ["feature_name", "stattest"])
ANALYSIS_ERRORS = Counter("evidently_analysis_errors_total", "Số lần phân tích lỗi")
LAST_ANALYSIS_TS = Gauge("evidently_last_analysis_timestamp_seconds",
                         "Unix time của lần phân tích thành công cuối")
REFERENCE_SAMPLES = Gauge("evidently_reference_samples", "Số dòng reference đang nạp")
BUFFER_SIZE = Gauge("evidently_production_buffer_size", "Số mẫu production đang giữ trong RAM")


# ---------------------------------------------------------------- schema request
class PredictionData(BaseModel):
    # Optional[float]: cho phép gửi null → thành NaN → đo được missing
    features: Dict[str, Optional[float]]
    prediction: Optional[float] = None
    timestamp: Optional[str] = None
    model_version: Optional[str] = None


class BatchPredictionData(BaseModel):
    data: List[Dict[str, Any]]
    feature_names: Optional[List[str]] = None


class ReferenceDataRequest(BaseModel):
    data: List[Dict[str, Any]]
    feature_names: Optional[List[str]] = None
    description: Optional[str] = None


class AnalyzeRequest(BaseModel):
    window_size: Optional[int] = Field(None, ge=1, description="None → EVIDENTLY_DEFAULT_WINDOW")
    # Tên `threshold` giữ cho tương thích tutorial07. Ý nghĩa ở đây: drift_share — tỷ lệ cột drift
    # để kết luận cả dataset drift (DAG tutorial07 cũng hiểu threshold là ngưỡng share).
    threshold: Optional[float] = Field(None, gt=0, le=1, description="None → EVIDENTLY_DRIFT_SHARE")
    # Ngưỡng của TỪNG kiểm định (p-value hoặc khoảng cách). None → mặc định của Evidently.
    stattest_threshold: Optional[float] = Field(None, gt=0)


# ---------------------------------------------------------------- lưu trữ
class DataStore:
    """reference lưu đĩa (volume) → sống qua restart; buffer production chỉ ở RAM → mất khi restart."""

    def __init__(self):
        self.lock = threading.Lock()
        self.reference: Optional[pd.DataFrame] = None
        self.reference_meta: Dict[str, Any] = {}
        self.buffer: List[Dict[str, Any]] = []
        self.last_analysis: Optional[datetime] = None
        self._load_reference()

    def _load_reference(self):
        csv = REFERENCE_DIR / "reference_data.csv"
        if csv.exists():
            self.reference = pd.read_csv(csv)
            meta = REFERENCE_DIR / "metadata.json"
            self.reference_meta = json.loads(meta.read_text()) if meta.exists() else {}
            REFERENCE_SAMPLES.set(len(self.reference))
            log.info("Nạp reference từ đĩa: %d dòng", len(self.reference))

    def save_reference(self, df: pd.DataFrame, meta: Dict[str, Any]):
        df.to_csv(REFERENCE_DIR / "reference_data.csv", index=False)
        (REFERENCE_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))
        with self.lock:
            self.reference, self.reference_meta = df, meta
        REFERENCE_SAMPLES.set(len(df))

    def add(self, rows: List[Dict[str, Any]]):
        with self.lock:
            self.buffer.extend(rows)
            self.buffer = self.buffer[-BUFFER_MAX:]
            BUFFER_SIZE.set(len(self.buffer))

    def window(self, n: Optional[int]) -> pd.DataFrame:
        with self.lock:
            rows = list(self.buffer[-n:]) if n else list(self.buffer)
        return pd.DataFrame(rows)

    def clear(self):
        with self.lock:
            self.buffer = []
        BUFFER_SIZE.set(0)


store = DataStore()
app = FastAPI(title="Evidently service (evidently-course bài 04)", version="1.0.0")


# ---------------------------------------------------------------- phân tích
def run_analysis(reference: pd.DataFrame, current: pd.DataFrame, drift_share: float,
                 stattest_threshold: Optional[float]) -> Dict[str, Any]:
    cols = [c for c in reference.columns if c in current.columns and c not in EXCLUDE_COLS]
    if not cols:
        raise ValueError("reference và current không có feature chung")
    ref_df, cur_df = reference[cols], current[cols]

    kwargs: Dict[str, Any] = {"drift_share": drift_share}
    if stattest_threshold is not None:
        kwargs["stattest_threshold"] = stattest_threshold
    report = Report(metrics=[DataDriftPreset(**kwargs)])
    report.run(reference_data=ref_df, current_data=cur_df)

    # SỬA LỖI 1: tra metric theo tên; drift từng cột nằm ở DataDriftTable
    by_name = {m["metric"]: m["result"] for m in report.as_dict()["metrics"]}
    ds = by_name["DatasetDriftMetric"]
    # ép về kiểu Python thuần: numpy.bool_ làm FastAPI không trả JSON được
    columns = {c: {"drift_detected": bool(info["drift_detected"]),
                   "drift_score": float(info["drift_score"]),
                   "stattest_name": str(info["stattest_name"])}
               for c, info in by_name["DataDriftTable"]["drift_by_columns"].items()}

    drifted = [c for c, info in columns.items() if info["drift_detected"]]
    missing = {c: float(v) for c, v in cur_df.isna().mean().round(4).items()}

    # clear() trước khi set: nếu feature bị bỏ khỏi reference, series cũ không nằm lại mãi
    FEATURE_DRIFT.clear()
    FEATURE_DRIFT_SCORE.clear()
    MISSING_VALUES.clear()
    for col, info in columns.items():
        FEATURE_DRIFT.labels(feature_name=col).set(1 if info["drift_detected"] else 0)
        FEATURE_DRIFT_SCORE.labels(feature_name=col, stattest=info["stattest_name"]).set(info["drift_score"])
    for col, ratio in missing.items():
        MISSING_VALUES.labels(feature_name=col).set(ratio)

    # SỬA LỖI 3: luôn xuất share thật (0.27 vẫn là 0.27, không bị ép về 0)
    DRIFT_DETECTED.set(1 if ds["dataset_drift"] else 0)
    DRIFT_SCORE.set(ds["share_of_drifted_columns"])
    DRIFTED_FEATURES_COUNT.set(len(drifted))

    name = f"drift_report_{datetime.now():%Y%m%d_%H%M%S_%f}.html"
    report.save_html(str(REPORTS_DIR / name))
    for old in sorted(REPORTS_DIR.glob("drift_report_*.html"))[:-KEEP_REPORTS]:
        old.unlink(missing_ok=True)

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "drift_detected": bool(ds["dataset_drift"]),
        "drift_score": float(ds["share_of_drifted_columns"]),
        "drift_share": float(ds["drift_share"]),
        "drifted_features": drifted,
        "drift_scores": {c: info["drift_score"] for c, info in columns.items()},
        "stattests": {c: info["stattest_name"] for c, info in columns.items()},
        "missing_ratio": missing,
        "total_features": len(columns),
        "drifted_count": len(drifted),
        "report_url": f"/reports/{name}",
        "report_filename": name,
        "reference_samples": len(ref_df),
        "current_samples": len(cur_df),
    }


# ---------------------------------------------------------------- endpoint
@app.get("/")
def root():
    return {"service": "evidently-course-04", "endpoints": [
        "/health", "/metrics", "POST /capture", "POST /capture/batch", "GET|POST /reference",
        "POST /analyze", "/reports", "/reports/{name}", "DELETE /production-data"]}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "reference_data_loaded": store.reference is not None,
        "production_data_count": len(store.buffer),
        "last_analysis": store.last_analysis.isoformat() if store.last_analysis else None,
        "reports_count": len(list(REPORTS_DIR.glob("*.html"))),
    }


@app.post("/capture")
def capture(data: PredictionData):
    row = {**data.features, "prediction": data.prediction,
           "timestamp": data.timestamp or datetime.now().isoformat(), "model_version": data.model_version}
    store.add([row])
    return {"status": "success", "total_samples": len(store.buffer)}


@app.post("/capture/batch")
def capture_batch(data: BatchPredictionData):
    store.add(data.data)
    return {"status": "success", "captured": len(data.data), "total_samples": len(store.buffer)}


@app.get("/reference")
def reference_info():
    if store.reference is None:
        return {"loaded": False}
    return {"loaded": True, "samples": len(store.reference),
            "features": list(store.reference.columns), "metadata": store.reference_meta}


@app.post("/reference")
def upload_reference(req: ReferenceDataRequest):
    df = pd.DataFrame(req.data)
    if df.empty:
        raise HTTPException(400, "reference rỗng")
    meta = {"description": req.description or "reference", "uploaded_at": datetime.now().isoformat(),
            "samples": len(df), "features": req.feature_names or list(df.columns)}
    store.save_reference(df, meta)
    log.info("Reference mới: %d dòng", len(df))
    return {"status": "success", "samples": len(df), "features": list(df.columns)}


# `def` chứ không phải `async def`: Evidently tính toán nặng CPU. Trong `async def` nó chạy
# ngay trên event loop → cả service (kể cả /metrics cho Prometheus) đứng hình tới khi xong.
# `def` được FastAPI đẩy sang threadpool.
@app.post("/analyze")
def analyze(req: Optional[AnalyzeRequest] = None):
    req = req or AnalyzeRequest()
    if store.reference is None:
        raise HTTPException(400, "Chưa có reference. POST /reference trước.")
    current = store.window(req.window_size or DEFAULT_WINDOW)
    if len(current) < MIN_SAMPLES:
        # 400 = "chưa đủ điều kiện", DAG tutorial07 coi là skipped chứ không failed
        raise HTTPException(400, f"Mới có {len(current)} mẫu, cần >= {MIN_SAMPLES} (EVIDENTLY_MIN_SAMPLES)")

    start = time.perf_counter()
    try:
        result = run_analysis(store.reference, current, req.threshold or DEFAULT_DRIFT_SHARE,
                              req.stattest_threshold)
    except Exception as e:
        ANALYSIS_ERRORS.inc()
        log.exception("Phân tích lỗi")
        raise HTTPException(500, str(e))
    duration = time.perf_counter() - start

    ANALYSIS_COUNT.inc()
    ANALYSIS_DURATION.observe(duration)
    LAST_ANALYSIS_TS.set_to_current_time()
    store.last_analysis = datetime.now()
    result["duration_seconds"] = round(duration, 3)
    log.info("Phân tích xong %.2fs: drift=%s share=%.2f", duration, result["drift_detected"],
             result["drift_score"])
    return result


@app.get("/reports")
def list_reports():
    files = sorted(REPORTS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"count": len(files), "reports": [
        {"filename": p.name, "url": f"/reports/{p.name}", "size_kb": round(p.stat().st_size / 1024, 1)}
        for p in files]}


@app.get("/reports/{name}", response_class=HTMLResponse)
def get_report(name: str):
    path = REPORTS_DIR / name
    # chỉ cho đọc file .html nằm ngay trong REPORTS_DIR
    if Path(name).name != name or path.suffix != ".html" or not path.exists():
        raise HTTPException(404, "Không có report này")
    return path.read_text()


@app.delete("/production-data")
def clear_production():
    store.clear()
    return {"status": "success"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
