"""
BÀI 10 — API phục vụ model từ MLflow Registry. Bản gọn của tutorial07/api/main.py, cùng endpoint
mà DAG dùng: /health, /model/info, POST /model/reload, POST /predict, /metrics.

Sửa so với tutorial07:
  - endpoint dùng `def` (không `async def`): load model là việc chặn (I/O + unpickle); trong
    async def nó chặn cả event loop → mọi request khác đứng chờ trong lúc reload.
  - gauge model_version_info được .clear() trước khi set → reload không để lại series version cũ.
  - load bằng alias nếu đặt MODEL_ALIAS, ngược lại bằng stage (mặc định Production như tutorial07).
"""
import logging
import os
import threading
import time
from typing import List, Optional

import mlflow
import mlflow.pyfunc
import numpy as np
from fastapi import FastAPI, HTTPException
from mlflow.tracking import MlflowClient
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from pydantic import BaseModel
from starlette.responses import Response

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MODEL_NAME", "wine_quality_model")
MODEL_STAGE = os.getenv("MODEL_STAGE", "Production")
MODEL_ALIAS = os.getenv("MODEL_ALIAS", "")          # vd "champion"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")

PREDICTIONS = Counter("model_predictions_total", "Số lần dự đoán", ["model_name", "model_version"])
MODEL_VERSION = Gauge("model_version_info", "Version đang phục vụ", ["model_name", "version"])
MODEL_LOAD_TIME = Gauge("model_load_time_seconds", "Thời gian load model", ["model_name"])
RELOADS = Counter("model_reload_total", "Số lần reload", ["result"])


class ModelHolder:
    def __init__(self) -> None:
        self.model = None
        self.version: Optional[str] = None
        self.uri: Optional[str] = None
        self.load_time: Optional[float] = None
        # Hai request reload cùng lúc không được load chồng lên nhau
        self._lock = threading.Lock()
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    def load(self) -> bool:
        with self._lock:
            started = time.time()
            client = MlflowClient()
            try:
                if MODEL_ALIAS:
                    uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"
                    version = client.get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS).version
                else:
                    uri = f"models:/{MODEL_NAME}/{MODEL_STAGE}"
                    latest = client.get_latest_versions(MODEL_NAME, stages=[MODEL_STAGE])
                    if not latest:
                        raise RuntimeError(f"Chưa có version nào ở stage {MODEL_STAGE}")
                    version = latest[0].version
                # Tải artifact từ MinIO (cần MLFLOW_S3_ENDPOINT_URL + key) rồi unpickle
                model = mlflow.pyfunc.load_model(uri)
            except Exception as exc:  # noqa: BLE001 — model chưa có / MLflow chưa lên: API vẫn sống
                log.error("Load model thất bại: %s", exc)
                return False

            self.model, self.version, self.uri = model, str(version), uri
            self.load_time = time.time() - started
            MODEL_VERSION.clear()
            MODEL_VERSION.labels(model_name=MODEL_NAME, version=self.version).set(int(self.version))
            MODEL_LOAD_TIME.labels(model_name=MODEL_NAME).set(self.load_time)
            log.info("Đã load %s (v%s) trong %.2fs", uri, self.version, self.load_time)
            return True


holder = ModelHolder()
app = FastAPI(title="airflow-course-10 model API")
started_at = time.time()


@app.on_event("startup")
def startup() -> None:
    # Lần đầu bật stack chưa có model nào → load fail, API vẫn chạy, /health báo unhealthy.
    # DAG retrain promote xong sẽ gọi /model/reload.
    holder.load()


class PredictRequest(BaseModel):
    features: List[float]      # 13 số theo thứ tự cột của sklearn load_wine


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy" if holder.model is not None else "unhealthy",
        "model_loaded": holder.model is not None,
        "model_name": MODEL_NAME,
        "model_version": holder.version or "unknown",
        "uptime_seconds": round(time.time() - started_at, 1),
    }


@app.get("/model/info")
def model_info() -> dict:
    if holder.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"model_name": MODEL_NAME, "model_version": holder.version, "model_uri": holder.uri,
            "load_time_seconds": holder.load_time, "tracking_uri": MLFLOW_TRACKING_URI}


@app.post("/model/reload")
def reload_model() -> dict:
    if not holder.load():
        RELOADS.labels(result="failed").inc()
        raise HTTPException(status_code=500, detail="Model reload failed")
    RELOADS.labels(result="success").inc()
    return {"status": "success", "message": "Model reloaded successfully", "model_version": holder.version}


@app.post("/predict")
def predict(req: PredictRequest) -> dict:
    if holder.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if len(req.features) != 13:
        raise HTTPException(status_code=400, detail=f"Cần 13 feature (load_wine), nhận {len(req.features)}")
    pred = holder.model.predict(np.array(req.features).reshape(1, -1))
    PREDICTIONS.labels(model_name=MODEL_NAME, model_version=holder.version).inc()
    return {"prediction": int(pred[0]), "model_name": MODEL_NAME, "model_version": holder.version}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
