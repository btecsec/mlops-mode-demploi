"""Corrigé des tests du Chapitre 3 — la donnée.

À ce stade du fil rouge, il n'existe encore aucun package `churn_predictor` :
le test lit le CSV directement, exactement comme le notebook. C'est le
Chapitre 4 qui rendra cette logique importable — et ces tests plus courts.

Lancer depuis `chapitre-03/solution/` :  pytest ../tests -v
"""

from pathlib import Path

import pandas as pd
import pytest

# Le test tourne depuis solution/, où bootstrap.py a déposé le CSV.
CSV_PATH = Path(__file__).resolve().parents[1] / "solution" / "data" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    if not CSV_PATH.exists():
        pytest.skip(f"Dataset absent : lancez `python bootstrap.py 1` ({CSV_PATH})")
    return pd.read_csv(CSV_PATH)


def test_dataset_shape(df):
    """7043 clients, 21 colonnes : la forme de référence de tout le livre."""
    assert df.shape == (7043, 21)


def test_churn_rate_is_realistic(df):
    """Baseline métier : ~26,5 % de départs réels."""
    rate = (df["Churn"] == "Yes").mean()
    assert 0.26 < rate < 0.27


def test_target_is_binary(df):
    """La cible ne prend que deux valeurs — sinon ce n'est plus une classification binaire."""
    assert set(df["Churn"].unique()) == {"Yes", "No"}


def test_total_charges_has_blank_values(df):
    """Les 11 lignes à TotalCharges vide : le piège que le notebook nettoie avant d'entraîner."""
    blancs = (df["TotalCharges"].astype(str).str.strip() == "").sum()
    assert blancs == 11
