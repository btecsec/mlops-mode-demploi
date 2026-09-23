"""Corrigé des tests du Chapitre 4.

Deux assertions qui verrouillent la forme et la baseline du dataset. Un échec
ici veut dire une seule chose : « vos données ont changé » — dit dès le
chapitre 4, pas six mois plus tard en production.

Lancer depuis `chapitre-04/solution/` :  pytest -v
"""

from churn_predictor.data import churn_rate, load_raw_data


def test_dataset_shape():
    """7043 clients, 21 colonnes : la forme de référence du fil rouge."""
    df = load_raw_data()
    assert df.shape == (7043, 21)


def test_churn_rate_is_realistic():
    """Fourchette large volontairement : le test doit détecter un dataset
    remplacé par autre chose, pas hurler pour 0,3 point d'écart."""
    df = load_raw_data()
    rate = churn_rate(df)
    assert 0.20 < rate < 0.30  # baseline mesurée au chapitre 3
