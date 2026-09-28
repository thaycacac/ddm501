"""
API chấm điểm WDBC có gắn metric (= tutorial06/app/main.py, chưa có TRAP).

Chạy:  uvicorn app.main:app --port 28000
"""
import json
import os
import random
import time
from collections import deque
from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from app.metrics import (ERRORS, LATENCY, MALIGNANT_SHARE, MODEL_INFO,
                         MODEL_LOADED, PREDICTIONS, TRAP)

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
THRESHOLD = 0.5
WINDOW = 200

# Không có trong tutorial06 — chỉ để bài 06–07 giả lập model chậm.
# SLOW_MS=200 → 10% request bị chậm thêm 200 ms (trung bình tăng ít, p99 tăng vọt).
SLOW_MS = float(os.getenv("SLOW_MS", "0"))
SLOW_SHARE = 0.1

app = FastAPI(title="WDBC diagnosis API (prometheus-course 03)", version="1.0.0")

state: Dict[str, object] = {"model": None, "card": None}
# deque(maxlen=200): đầy thì tự đẩy phần tử cũ nhất ra → luôn là 200 dự đoán gần nhất.
recent: deque = deque(maxlen=WINDOW)


class PredictRequest(BaseModel):
    sample_id: str = Field(..., examples=["WDBC-0001"])
    # Dict thay vì 30 field cố định: thiếu feature KHÔNG bị Pydantic chặn (422 tự động)
    # mà đi vào code của ta → ta đếm được lỗi đó theo reason="missing_features".
    features: Dict[str, float]


# Tutorial06 dùng on_event("startup") — cách cũ của `lifespan`, cùng tác dụng.
# Giữ nguyên để đọc tutorial06 khớp từng dòng.
@app.on_event("startup")
def load_model() -> None:
    path = MODELS / "model.joblib"
    if not path.exists():
        # Không có model: process vẫn chạy, nhưng gauge báo 0.
        # Alert ModelNotLoaded (bài 07) dựa vào đúng con số này.
        MODEL_LOADED.set(0)
        return
    state["model"] = joblib.load(path)
    state["card"] = json.loads((MODELS / "model_card.json").read_text())
    MODEL_LOADED.set(1)
    MODEL_INFO.labels(version=state["card"]["version"],
                      sklearn_version=state["card"]["sklearn_version"]).set(1)


@app.get("/health")
def health() -> dict:
    return {"status": "ok" if state["model"] else "degraded",
            "model_loaded": state["model"] is not None,
            "version": (state["card"] or {}).get("version")}


@app.post("/predict")
def predict(req: PredictRequest) -> dict:
    if state["model"] is None:
        ERRORS.labels(reason="model_not_loaded").inc()
        raise HTTPException(status_code=503, detail="model not loaded")

    features: List[str] = state["card"]["features"]
    missing = [f for f in features if f not in req.features]
    if missing:
        # Lỗi phía client → vẫn đếm, vì tỉ lệ lỗi tăng vọt thường là dấu hiệu
        # một client vừa deploy bản sai (đổi tên field, bỏ field...).
        ERRORS.labels(reason="missing_features").inc()
        raise HTTPException(status_code=422,
                            detail=f"missing features: {missing[:3]}")

    # Đồng hồ chỉ bao đúng phần "dự đoán". Request lỗi phía trên không được observe
    # → histogram chỉ nói về dự đoán thành công, lỗi đã có ERRORS lo.
    start = time.perf_counter()
    frame = pd.DataFrame([[req.features[f] for f in features]], columns=features)
    probability = float(state["model"].predict_proba(frame)[0, 1])
    if SLOW_MS and random.random() < SLOW_SHARE:
        time.sleep(SLOW_MS / 1000)
    LATENCY.observe(time.perf_counter() - start)

    outcome = "malignant" if probability >= THRESHOLD else "benign"
    labels = {"outcome": outcome}
    if TRAP:
        # sample_id do NGƯỜI DÙNG gửi lên, không giới hạn → mỗi giá trị mới = một series mới.
        labels["sample_id"] = req.sample_id
    PREDICTIONS.labels(**labels).inc()

    recent.append(1 if outcome == "malignant" else 0)
    MALIGNANT_SHARE.set(sum(recent) / len(recent))

    return {"sample_id": req.sample_id, "probability": round(probability, 6),
            "outcome": outcome, "threshold": THRESHOLD,
            "model_version": state["card"]["version"]}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    # generate_latest() in mọi metric trong REGISTRY mặc định theo exposition format.
    # CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; ..." — header Prometheus mong đợi.
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
