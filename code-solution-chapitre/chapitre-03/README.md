# Chapitre 3 — Le dataset du fil rouge et le premier modèle

Le dataset entre en scène : 7043 clients, 21 colonnes, un modèle entraîné pour
de vrai. Tout se passe dans un unique notebook, avec des chemins en dur et zéro
fonction — c'est **volontaire**. C'est l'état « ça marche sur mon PC » que le
Chapitre 4 va démonter.

## Ce que le chapitre ajoute

- `data/WA_Fn-UseC_-Telco-Customer-Churn.csv` — le dataset Telco Customer Churn
- `solution/exploration.ipynb` — exploration, nettoyage, entraînement, évaluation
- `model.pkl` — produit par le notebook, jamais commité (voir `.gitignore`)

## Contenu

```text
chapitre-03/
├── README.md
├── exercice.md
├── solution/
│   └── exploration.ipynb          # notebook corrigé, commenté cellule par cellule
└── tests/
    ├── test_data_loading.py       # forme (7043, 21), taux de churn, 11 TotalCharges vides
    └── test_premier_modele.py     # ré-entraîne le pipeline et vérifie ses métriques
```

## Lancer la solution

```bash
python ../../bootstrap.py 3     # dépose le CSV dans solution/data/
cd solution
python -m venv venv
source venv/Scripts/activate    # PowerShell : venv\Scripts\Activate.ps1
pip install pandas scikit-learn joblib jupyter pytest
jupyter notebook exploration.ipynb
```

## Résultat attendu

```text
(7043, 21)
Baseline : 0.7353
Accuracy test  : 0.7913
Accuracy train : 0.9986
[[942  94]
 [200 173]]
              precision    recall  f1-score   support

           0       0.82      0.91      0.87      1036
           1       0.65      0.46      0.54       373
```

Trois lectures, dans cet ordre :

| Ce qu'on lit | Ce que ça veut dire |
|---|---|
| 0,7913 en test contre 0,7353 de baseline | Le modèle apporte 5,6 points. Réel, mais modeste |
| 0,9986 en train contre 0,7913 en test | Surapprentissage : la forêt a mémorisé le jeu d'entraînement |
| Recall de 0,46 sur la classe 1 | 173 départs vus sur 373. **Il en rate 200** |

Ce modèle n'est pas bon, et c'est le sujet du livre : les quinze chapitres
suivants construisent la machinerie qui permet de l'améliorer, de le comparer à
ses successeurs et de le remplacer sans casse.

## Lancer les tests

```bash
pytest ../tests -v
```

`test_premier_modele.py` ré-entraîne le pipeline à chaque exécution (une
dizaine de secondes) : c'est le prix d'un test qui vérifie vraiment le
comportement du modèle plutôt qu'un `.pkl` figé.

## Le détail qui coince toujours

`TotalCharges` arrive en `object` alors qu'elle contient des montants : onze
clients d'ancienneté nulle y ont un espace vide. Sans
`pd.to_numeric(..., errors="coerce").fillna(0)`, l'entraînement s'arrête sur
`ValueError: could not convert string to float: ' '`. Onze lignes sur 7043,
soit 0,15 % du dataset, bloquent 100 % du projet.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `FileNotFoundError` sur `data/WA_Fn-UseC_-...csv` | Le notebook n'a pas été lancé depuis la racine du projet | Relancer `jupyter notebook` depuis la racine : le chemin est relatif au dossier de travail |
| `ValueError: could not convert string to float: ' '` | La conversion de `TotalCharges` de l'Étape 3 a été sautée, ou le notebook rouvert sans la rejouer | Réexécuter les cellules depuis le début |
| `ModuleNotFoundError: No module named 'sklearn'` | Le noyau du notebook n'est pas celui du `venv` | *Kernel → Change kernel*, ou relancer Jupyter depuis le `venv` activé |
| Accuracy de test proche de `1.00` | Une colonne trahit la réponse : `customerID` ou `Churn` est resté dans `X` | Le piège classique de ce chapitre |
| Des chiffres différents de ceux du livre | `random_state=42` manque au découpage ou à la forêt | Le remettre aux deux endroits |
