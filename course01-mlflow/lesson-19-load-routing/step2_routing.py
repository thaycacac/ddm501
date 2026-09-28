"""
BÀI 19 — Bước 2: tutorial02-extend/05_model_routing.py, viết lại có comment.

  python step2_routing.py          như extend: load_model trong MỖI request (20 request)
  python step2_routing.py cached   load mỗi alias MỘT lần rồi dùng lại (1000 request)

Cả hai: 90% → @prod (v1), 10% → @dev (v2). In tỉ lệ thực tế + thời gian.
"""
from __future__ import annotations

import sys
import time
from collections import Counter

import mlflow.pyfunc
import numpy as np

from connect import MODEL_NAME, connect
from data import get_data

TRAFFIC_SPLIT = 0.9
rng = np.random.default_rng(42)  # seed → chạy lại ra cùng dãy random, dễ so sánh


def pick_alias(traffic_split: float) -> str:
    # Mỗi request tung đồng xu lệch: < 0.9 → prod, còn lại → dev
    return "prod" if rng.random() < traffic_split else "dev"


def get_model_for_prediction(model_name: str, traffic_split: float = TRAFFIC_SPLIT):
    """Y như extend: chọn alias rồi load_model ngay trong request."""
    alias = pick_alias(traffic_split)
    model = mlflow.pyfunc.load_model(f"models:/{model_name}@{alias}")
    return model, alias


_cache: dict[str, mlflow.pyfunc.PyFuncModel] = {}


def get_model_cached(model_name: str, traffic_split: float = TRAFFIC_SPLIT):
    """Chỉ load lần đầu gặp alias. Đánh đổi: ship prod mới thì phải restart/xoá cache."""
    alias = pick_alias(traffic_split)
    if alias not in _cache:
        _cache[alias] = mlflow.pyfunc.load_model(f"models:/{model_name}@{alias}")
    return _cache[alias], alias


def main() -> None:
    connect()
    _, X_test, _, _ = get_data()

    cached = sys.argv[1:] == ["cached"]
    n_requests = 1000 if cached else 20
    get_model = get_model_cached if cached else get_model_for_prediction

    counts: Counter[str] = Counter()
    start = time.perf_counter()
    for i in range(n_requests):
        model, alias = get_model(MODEL_NAME)
        sample = X_test[i % len(X_test)].reshape(1, -1)  # 1 request = 1 bệnh nhân
        pred = model.predict(sample)[0]
        counts[alias] += 1
        if i < 10:
            print(f"request {i:>2} → @{alias:<4}  pred={pred}")
    elapsed = time.perf_counter() - start

    print(f"\nmode      = {'cached' if cached else 'load mỗi request (extend)'}")
    print(f"requests  = {n_requests}   prod={counts['prod']}  dev={counts['dev']}  "
          f"(dev ≈ {counts['dev'] / n_requests:.0%}, kỳ vọng {1 - TRAFFIC_SPLIT:.0%})")
    print(f"thời gian = {elapsed:.2f}s   ≈ {elapsed / n_requests * 1000:.1f} ms/request")


if __name__ == "__main__":
    main()
