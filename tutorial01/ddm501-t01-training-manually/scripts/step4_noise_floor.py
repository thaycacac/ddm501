"""
Step 4 — is the winner?

Run:  python scripts/step4_noise_floor.py
"""
import warnings

import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV, RepeatedStratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

GRID = {
    "randomforestclassifier__n_estimators": [50, 100, 200, 400],
    "randomforestclassifier__max_depth": [3, 5, 8, None],
    "randomforestclassifier__min_samples_leaf": [1, 2, 4, 8],
    "randomforestclassifier__max_features": ["sqrt", "log2", 0.5],
}


def main() -> None:
    X, y = load_breast_cancer(as_frame=True, return_X_y=True)

    # 5 folds repeated 3 times = 15 estimates per configuration instead of 5.
    # A single 5-fold score is one draw from a distribution; you cannot see the
    # width of that distribution from one draw, which is exactly the mistake
    # step 2 makes.
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0)
    search = RandomizedSearchCV(
        make_pipeline(StandardScaler(), RandomForestClassifier(random_state=0)),
        GRID, n_iter=30, scoring="roc_auc", cv=cv, random_state=0, n_jobs=-1)
    search.fit(X, y)

    res = search.cv_results_
    order = np.argsort(-res["mean_test_score"])[:10]

    print("top 10 configurations   (roc_auc, RepeatedStratifiedKFold 5 x 3)\n")
    for rank, i in enumerate(order, 1):
        mean, std = res["mean_test_score"][i], res["std_test_score"][i]
        bar = "#" * int(round((mean - 0.985) * 4000))
        print(f"  {rank:2d}. {mean:.5f}  +/- {std:.5f}  {bar}")

    best, tenth = res["mean_test_score"][order[0]], res["mean_test_score"][order[9]]
    std_best = res["std_test_score"][order[0]]
    gap = best - tenth

    print(f"\n  gap, rank 1 to rank 10   {gap:.5f}")
    print(f"  std deviation of rank 1  {std_best:.5f}")
    if gap < std_best:
        print(f"\n  The spread of the winner is {std_best / gap:.1f}x larger than the gap it "
              f"won by.\n  On 569 rows, the ranking of the top ten is noise. 'Best model'\n"
              f"  is not a number you can read off a single score.")
    else:
        print("\n  The gap is larger than the spread; the ranking is meaningful here.")

    print("""
Which turns the problem from step 2 into a harder one. It is not enough to
record the winning score. To make a defensible claim you have to record, for
every run: the score, its spread, the fold structure, every seed, and the
library versions. Try adding four more columns to logs/results.csv by hand
""")


if __name__ == "__main__":
    main()
