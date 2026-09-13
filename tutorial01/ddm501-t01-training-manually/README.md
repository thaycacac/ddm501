# Tutorial 01 — Training a model by hand

**DDM501 — AI in DevOps, DataOps, MLOps **

Read the manual (`DDM501_T01_Training_By_Hand.pdf`) alongside these
scripts.

## Purposes

You will train roughly 40 models without any experiment tracking tool, and
then be asked questions about them.

## Environment requirements

Python 3.11 or higher

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Steps

| Script | What it does | Runtime |
|---|---|---|
| `scripts/step1_baseline.py` | One random forest, one score. Ends with five questions to answer on paper. |
| `scripts/step2_random_search.py` | 30 configurations across three types of model. Run it three times with different flags. |
| `scripts/step3_logbook.py` | The CSV logbook you would have written yourself — and what it still cannot record. |
| `scripts/step4_noise_floor.py` | Repeated cross-validation. Asks whether the winner actually won. |

```bash
python scripts/step1_baseline.py
python scripts/step2_random_search.py
python scripts/step2_random_search.py --seed 7
python scripts/step2_random_search.py --no-scaling
python scripts/step3_logbook.py --tag baseline
python scripts/step3_logbook.py --tag deep --max-depth 3
python scripts/step3_logbook.py --tag baseline --n-estimators 400
python scripts/step4_noise_floor.py
```

## About the data

The Wisconsin Diagnostic Breast Cancer set: 569 samples, 30 features, 212
malignant and 357 benign. The features are measurements of cell nuclei taken
from digitised images of fine needle aspirates, published in 1995.

The model predicts **the label a pathologist assigned**, not a diagnosis.

Note the encoding: `0 = malignant`, `1 = benign`. 