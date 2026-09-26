"""
Step 3 — the registry: names, versions, aliases.

Run:  python scripts/step3_register.py
"""
import mlflow
from mlflow import MlflowClient

from _common import EXPERIMENT, MODEL_NAME, connect


def register(run_id: str, note: str) -> int:
    """Copy one run's model into the registry and return its version number."""
    mv = mlflow.register_model(f"runs:/{run_id}/model", MODEL_NAME)
    MlflowClient().update_model_version(
        name=MODEL_NAME, version=mv.version, description=note)
    return int(mv.version)


def main() -> None:
    connect()
    client = MlflowClient()

    runs = mlflow.search_runs(experiment_names=[EXPERIMENT],
                              order_by=["metrics.cv_roc_auc_mean DESC"])
    first, second = runs.iloc[0], runs.iloc[1]

    v1 = register(first["run_id"], "best cv_roc_auc_mean")
    v2 = register(second["run_id"], "runner-up, different family, simpler")
    print(f"registered version {v1}: {first['tags.mlflow.runName']}")
    print(f"registered version {v2}: {second['tags.mlflow.runName']}")

    # An alias is a movable pointer to one version. Code refers to the alias,
    # never to a version number, so promoting a model is a metadata change and
    # not a code change. MLflow 2.x replaced the old Staging/Production stages
    # with aliases -- Lab 2 uses aliases, so learn these, not stages.
    client.set_registered_model_alias(MODEL_NAME, "champion", str(v1))
    client.set_registered_model_alias(MODEL_NAME, "challenger", str(v2))
    show(client)

    print("\nNow promote the challenger. Watch what does and does not change.\n")
    client.set_registered_model_alias(MODEL_NAME, "champion", str(v2))
    client.delete_registered_model_alias(MODEL_NAME, "challenger")
    show(client)

    print("""
  1. Open http://127.0.0.1:5000, go to the Models tab, open the model.
  2. Version 1 and version 2 are both listed, each linked back to the run
     that produced it.
  3. Run this script again. You will get versions 3 and 4, not an error and
     not an overwrite. That is what "versioning" means here.
""")


def show(client: MlflowClient) -> None:
    # search_model_versions does not fill in .aliases; the mapping lives on the
    # registered model as {alias: version}. Reading it the other way round is
    # a common half-hour lost.
    alias_of = {}
    for alias, version in client.get_registered_model(MODEL_NAME).aliases.items():
        alias_of.setdefault(str(version), []).append(alias)

    print(f"\n{'version':>8}  {'aliases':<24} description")
    for mv in sorted(client.search_model_versions(f"name='{MODEL_NAME}'"),
                     key=lambda m: int(m.version)):
        aliases = ", ".join(sorted(alias_of.get(str(mv.version), []))) or "-"
        print(f"{mv.version:>8}  {aliases:<24} {mv.description}")


if __name__ == "__main__":
    main()
