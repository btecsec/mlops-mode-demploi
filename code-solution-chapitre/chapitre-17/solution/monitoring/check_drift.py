"""Couche 2 du monitoring : la santé statistique du modèle.

Compare les données réellement reçues en production (le journal alimenté par
`/predict`, Chapitre 15) à la baseline d'entraînement (le dataset du Chapitre 3).
Un modèle qui se trompe ne lève aucune exception : il répond, avec confiance,
une prédiction simplement moins bonne qu'avant. Seule cette comparaison le voit
venir.

Usage :
    python monitoring/check_drift.py       # depuis solution/
"""

import pandas as pd

from churn_predictor.config import PREDICTIONS_LOG
from churn_predictor.data import load_raw_data

# Part de colonnes dérivées tolérée avant alerte. 0.3 est un point de départ,
# pas une vérité : le bon seuil se règle en observant la valeur en régime
# normal pendant quelques semaines.
DRIFT_THRESHOLD = 0.3

# Colonnes ajoutées par la journalisation, absentes du dataset d'entraînement.
COLONNES_JOURNAL = ["timestamp", "probability"]


def load_baseline() -> pd.DataFrame:
    """Le dataset d'entraînement, nettoyé exactement comme dans train.py.

    Sans le `to_numeric`, `TotalCharges` est comparée en texte côté baseline et
    en nombre côté production : Evidently choisit alors deux tests statistiques
    différents pour la même colonne, et annonce une dérive qui n'existe pas.
    """
    baseline = load_raw_data().drop(columns=["customerID", "Churn"])
    baseline["TotalCharges"] = pd.to_numeric(
        baseline["TotalCharges"], errors="coerce"
    ).fillna(0)
    return baseline


def load_production() -> pd.DataFrame:
    """Le journal des prédictions, ramené aux colonnes de la baseline."""
    if not PREDICTIONS_LOG.exists():
        raise SystemExit(
            "Journal de prédictions introuvable : appelez /predict au moins "
            "une fois avant de mesurer un drift."
        )
    return pd.read_csv(PREDICTIONS_LOG).drop(columns=COLONNES_JOURNAL, errors="ignore")


def align(baseline: pd.DataFrame, production: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restreint les deux tableaux aux colonnes communes, dans le même ordre.

    Une colonne présente d'un seul côté n'est pas comparable : la laisser
    passer fait échouer Evidently ou, pire, gonfle artificiellement le taux de
    dérive au premier ajout de champ dans le schéma d'entrée.
    """
    communes = [c for c in baseline.columns if c in production.columns]
    if not communes:
        raise SystemExit(
            "Aucune colonne commune entre la baseline et le journal — le "
            "schéma d'entrée a-t-il changé ?"
        )
    return baseline[communes], production[communes]


def check_drift() -> float:
    """Retourne la part de colonnes ayant statistiquement dérivé, entre 0 et 1.

    L'import d'Evidently est local à la fonction, volontairement : le reste du
    module (chargement, alignement, seuil) reste testable et importable sans
    installer une dépendance de plusieurs centaines de mégaoctets.

    API Evidently 0.7 : `Report` s'importe depuis `evidently`, les presets
    depuis `evidently.presets`, et `run()` rend un instantané au lieu de
    remplir le rapport. Voir requirements-monitoring.txt pour l'épinglage.
    """
    from evidently import Report
    from evidently.presets import DataDriftPreset

    baseline, production = align(load_baseline(), load_production())

    # DataDriftPreset compare colonne par colonne et choisit tout seul un test
    # statistique adapté au type de chaque colonne.
    report = Report(metrics=[DataDriftPreset()])
    snapshot = report.run(reference_data=baseline, current_data=production)

    # Le preset rend une métrique par colonne, précédée d'un décompte global :
    # DriftedColumnsCount, dont la valeur est {"count": ..., "share": ...}.
    part = snapshot.dict()["metrics"][0]["value"]["share"]
    print(f"Part de colonnes dérivées : {part:.0%}")
    return part


if __name__ == "__main__":
    part = check_drift()
    if part > DRIFT_THRESHOLD:
        raise SystemExit(
            f"Drift au-delà du seuil ({part:.0%} > {DRIFT_THRESHOLD:.0%})"
        )
