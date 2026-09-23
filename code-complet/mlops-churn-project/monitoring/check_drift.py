import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset

from churn_predictor.config import PREDICTIONS_LOG
from churn_predictor.data import load_raw_data

DRIFT_THRESHOLD = 0.3  # part de colonnes dérivées tolérée avant alerte


def check_drift() -> float:
    if not PREDICTIONS_LOG.exists():
        raise SystemExit(
            "Journal de prédictions introuvable : appelez /predict au moins "
            "une fois avant de mesurer un drift."
        )

    baseline = load_raw_data().drop(columns=["customerID", "Churn"])
    # Même nettoyage qu'à l'entraînement (Ch. 5) : sans lui, TotalCharges est
    # comparée en texte côté baseline et en nombre côté production.
    baseline["TotalCharges"] = pd.to_numeric(baseline["TotalCharges"], errors="coerce").fillna(0)

    production = pd.read_csv(PREDICTIONS_LOG).drop(columns=["timestamp", "probability"])

    report = Report(metrics=[DataDriftPreset()])
    # run() ne remplit pas le rapport : il rend un instantané, à lire séparément.
    snapshot = report.run(reference_data=baseline, current_data=production)

    # Première métrique du preset : DriftedColumnsCount, dont la valeur est un
    # dictionnaire {"count": 4.0, "share": 0.21}.
    drift_share = snapshot.dict()["metrics"][0]["value"]["share"]
    print(f"Part de colonnes dérivées : {drift_share:.0%}")
    return drift_share


if __name__ == "__main__":
    share = check_drift()
    if share > DRIFT_THRESHOLD:
        raise SystemExit(f"Drift au-delà du seuil ({share:.0%} > {DRIFT_THRESHOLD:.0%})")
