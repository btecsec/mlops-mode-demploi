# Chapitre 2 — Comprendre le ML avant de faire l'Ops

Le seul chapitre de théorie pure du livre. Aucune donnée réelle, aucun modèle
en production : on installe le vocabulaire (feature, label, train/test,
surapprentissage) et surtout les métriques, parce que ce sont elles qui
décideront plus tard de ce qui part en prod, de ce qui alerte et de ce qui
déclenche un rollback.

La démonstration tient sur dix clients fabriqués à la main. C'est justement
parce que le jeu est minuscule qu'on peut recompter chaque cas et vérifier ce
que scikit-learn affiche.

## Ce que le chapitre ajoute

- `solution/notebooks/metriques_demo.ipynb` — un modèle à 70 % d'accuracy et
  0 % de recall, puis une règle métier qui fait mieux sur les deux tableaux

## Contenu

```text
chapitre-02/
├── README.md
├── exercice.md
├── solution/
│   └── notebooks/
│       └── metriques_demo.ipynb   # notebook corrigé, commenté cellule par cellule
└── tests/
    └── test_metriques.py          # recalcule les deux modèles et vérifie les scores
```

Pas de dataset ici : `bootstrap.py` n'a rien à installer pour ce chapitre.

## Lancer la solution

```bash
cd solution
python -m venv venv
source venv/Scripts/activate      # PowerShell : venv\Scripts\Activate.ps1
pip install pandas scikit-learn jupyter
jupyter notebook notebooks/metriques_demo.ipynb
```

## Résultat attendu

Le modèle « personne ne part jamais » :

```text
Accuracy : 0.7
[[7 0]
 [3 0]]
```

La colonne de droite est vide : ce modèle n'a jamais prédit un seul départ.
Son recall sur la classe « part » vaut 0,00, alors que son accuracy affiche
0,70. C'est tout l'objet du chapitre.

La règle métier `contrat mensuel + facture > 80` :

```text
Accuracy : 0.9
[[6 1]
 [0 3]]
```

Trois départs sur trois détectés, une seule fausse alerte.

## Lancer les tests

```bash
pip install pytest pandas scikit-learn
pytest ../tests -v
```

Les tests reconstruisent les dix clients et vérifient les deux jeux de
métriques — si scikit-learn change de comportement, ils le signalent.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `jupyter : command not found` | Le `venv` n'est pas activé, ou jupyter n'y est pas installé | Le réactiver, puis `pip install jupyter` (Chapitre 1) |
| `SyntaxError` en lançant `python metriques_demo.ipynb` | Un `.ipynb` est du JSON, pas un script Python | L'ouvrir dans Jupyter, jamais l'exécuter directement |
| `ModuleNotFoundError: No module named 'pandas'` dans une cellule | Le noyau du notebook n'est pas celui du `venv` | *Kernel → Change kernel*, ou relancer `jupyter notebook` depuis le `venv` activé |
| `UndefinedMetricWarning` sur la précision de la classe `1` | Aucune prédiction positive : la précision vaut 0/0 | `zero_division=0`, déjà présent dans le code de l'Étape 4 |
