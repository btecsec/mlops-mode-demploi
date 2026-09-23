"""Corrigé des tests du Chapitre 2.

Aucun dataset, aucun package `churn_predictor` : ce chapitre ne manipule que
les dix clients fabriqués à la main dans le notebook. Les tests les
reconstruisent à l'identique et vérifient les deux jeux de métriques — si une
version de scikit-learn change de comportement, ils le signalent avant que le
livre ne devienne faux.

Lancer depuis `chapitre-02/solution/` :  pytest ../tests -v
"""

import pandas as pd
import pytest
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_score,
    recall_score,
)


@pytest.fixture(scope="module")
def clients() -> pd.DataFrame:
    """Les dix clients du notebook, à l'identique."""
    return pd.DataFrame({
        "anciennete_mois":   [2, 48, 1, 60, 3, 36, 24, 5, 72, 9],
        "facture_mensuelle": [85, 45, 95, 40, 88, 55, 60, 92, 38, 78],
        "contrat_mensuel":   [1, 0, 1, 0, 1, 0, 0, 1, 0, 1],
        "churn":             [1, 0, 1, 0, 0, 0, 0, 1, 0, 0],
    })


@pytest.fixture(scope="module")
def y(clients):
    return clients["churn"]


def test_jeu_desequilibre(y):
    """Sept clients sur dix restent : c'est ce 0,70 qui piège l'accuracy."""
    assert len(y) == 10
    assert (y == 0).mean() == 0.7


def test_baseline_a_une_bonne_accuracy(y):
    """Le modèle « personne ne part » atteint 0,70 sans rien apprendre."""
    y_pred = [0] * len(y)
    assert accuracy_score(y, y_pred) == 0.70


def test_baseline_ne_detecte_aucun_depart(y):
    """Précision et recall nuls sur la classe 1 : la valeur métier est nulle."""
    y_pred = [0] * len(y)
    assert recall_score(y, y_pred, zero_division=0) == 0.0
    assert precision_score(y, y_pred, zero_division=0) == 0.0


def test_baseline_ne_predit_jamais_la_classe_positive(y):
    """Toute la colonne « prédit positif » de la matrice de confusion est vide."""
    y_pred = [0] * len(y)
    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
    assert (tn, fp, fn, tp) == (7, 0, 3, 0)


def regle_metier(clients) -> list[int]:
    """Contrat mensuel + facture élevée = risque. Zéro apprentissage, une règle."""
    return [
        1 if (contrat == 1 and facture > 80) else 0
        for contrat, facture in zip(clients["contrat_mensuel"],
                                    clients["facture_mensuelle"])
    ]


def test_regle_metier_detecte_tous_les_departs(clients, y):
    """Recall de 1,00 : les trois départs réels sont vus."""
    y_pred = regle_metier(clients)
    assert recall_score(y, y_pred) == 1.0


def test_regle_metier_fait_une_fausse_alerte(clients, y):
    """Une seule fausse alerte, donc une précision de 0,75 — l'arbitrage assumé."""
    y_pred = regle_metier(clients)
    tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
    assert (tn, fp, fn, tp) == (6, 1, 0, 3)
    assert precision_score(y, y_pred) == 0.75
    assert accuracy_score(y, y_pred) == 0.90
