"""Corrigé des tests du Chapitre 3 — le modèle.

Ces tests ré-entraînent le pipeline du notebook à chaque exécution, sur le CSV
réel. C'est volontairement plus lent qu'un `.pkl` figé : ce qu'on veut vérifier,
c'est que le chemin complet (nettoyage → encodage → entraînement → évaluation)
produit encore les chiffres annoncés dans le livre.

À ce stade il n'existe aucun package `churn_predictor` : le test refait le
pipeline à la main, exactement comme le notebook. C'est le Chapitre 4 qui
rendra cette logique importable — et ces tests bien plus courts.

Lancer depuis `chapitre-03/solution/` :  pytest ../tests -v
"""

from pathlib import Path

import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

CSV_PATH = (Path(__file__).resolve().parents[1] / "solution" / "data"
            / "WA_Fn-UseC_-Telco-Customer-Churn.csv")


@pytest.fixture(scope="module")
def donnees():
    if not CSV_PATH.exists():
        pytest.skip(f"Dataset absent : lancez `python bootstrap.py 3` ({CSV_PATH})")
    df = pd.read_csv(CSV_PATH)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)
    X = df.drop(columns=["customerID", "Churn"])
    y = (df["Churn"] == "Yes").astype(int)
    return train_test_split(X, y, test_size=0.2, random_state=42)


@pytest.fixture(scope="module")
def modele(donnees):
    X_train, _, y_train, _ = donnees
    colonnes_texte = X_train.select_dtypes(include="object").columns.tolist()
    pipeline = Pipeline([
        ("prep", ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore"), colonnes_texte)],
            remainder="passthrough",
        )),
        ("model", RandomForestClassifier(n_estimators=200, random_state=42)),
    ])
    pipeline.fit(X_train, y_train)
    return pipeline


def test_decoupage_train_test(donnees):
    """80/20 sur 7043 lignes, et 19 features une fois customerID et Churn retirés."""
    X_train, X_test, _, _ = donnees
    assert X_train.shape == (5634, 19)
    assert X_test.shape == (1409, 19)


def test_baseline_du_jeu_de_test(donnees):
    """Le seuil à battre, calculé sur le jeu de test : 73,53 %."""
    _, _, _, y_test = donnees
    baseline = accuracy_score(y_test, [0] * len(y_test))
    assert round(baseline, 4) == 0.7353


def test_le_modele_bat_le_baseline(donnees, modele):
    """Utile, mais modestement : environ +5,6 points d'accuracy."""
    _, X_test, _, y_test = donnees
    accuracy = accuracy_score(y_test, modele.predict(X_test))
    assert accuracy > 0.7353, "un modèle sous le baseline n'a aucune raison d'exister"
    assert 0.77 < accuracy < 0.81


def test_le_modele_surapprend(donnees, modele):
    """0,99 en train contre 0,79 en test : la forêt a mémorisé son jeu d'entraînement."""
    X_train, X_test, y_train, y_test = donnees
    train = modele.score(X_train, y_train)
    test = modele.score(X_test, y_test)
    assert train > 0.99
    assert train - test > 0.15


def test_le_recall_est_le_vrai_resultat(donnees, modele):
    """Moins d'un départ sur deux détecté : le chiffre qui compte pour le métier."""
    _, X_test, _, y_test = donnees
    recall = recall_score(y_test, modele.predict(X_test))
    assert 0.40 < recall < 0.52, (
        "le modèle du Chapitre 3 rate volontairement la moitié des départs — "
        "c'est ce que les chapitres suivants outillent"
    )
