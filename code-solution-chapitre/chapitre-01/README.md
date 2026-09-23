# Chapitre 1 — Le métier MLOps en vrai

Point de départ absolu du fil rouge : rien n'existe encore. Ce chapitre ne
produit pas de modèle, il installe le terrain — un dépôt Git initialisé et un
environnement Python isolé, avec les trois seules bibliothèques nécessaires
jusqu'au Chapitre 5.

Le vocabulaire du Machine Learning arrive au Chapitre 2, le dataset au
Chapitre 3.

## Ce que le chapitre ajoute

- un dépôt `mlops-churn-project/` avec `git init`
- un `venv` local, activé
- `pandas`, `scikit-learn` et `jupyter` installés dedans

## Contenu

```text
chapitre-01/
├── README.md
├── exercice.md
├── solution/                    # volontairement vide : l'état de fin de chapitre
│   └── .gitkeep                 # est un environnement, pas des fichiers
└── tests/
    └── test_environnement.py    # vérifie Python >= 3.10 et les trois imports
```

`solution/` ne contient aucun fichier de code : à la fin de ce chapitre, le
projet *est* un dossier vide sous Git avec un `venv` à côté. C'est le seul
chapitre du livre dans ce cas.

## Lancer la solution

```bash
python --version    # 3.10 minimum
git --version

mkdir mlops-churn-project
cd mlops-churn-project
git init

python -m venv venv
source venv/Scripts/activate    # Git Bash sous Windows ; venv\Scripts\Activate.ps1 en PowerShell
pip install pandas scikit-learn jupyter
```

## Résultat attendu

```text
2.2.2 1.5.1
```

Les numéros exacts importent peu. Ce qui compte : la commande répond depuis le
`venv`, pas depuis le Python global.

## Lancer les tests

```bash
pip install pytest
pytest ../tests -v
```

Les trois tests vérifient la version de Python et la présence des trois
bibliothèques — c'est tout ce que ce chapitre promet.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `python` ouvre le Microsoft Store, ou reste sans effet | L'alias d'exécution d'application de Windows détourne la commande | Le désactiver dans *Paramètres → Applications → Alias d'exécution d'application*, ou taper `py` |
| `Activate.ps1 : l'exécution de scripts est désactivée sur ce système` | La politique d'exécution PowerShell bloque les scripts locaux | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, puis relancer l'activation |
| `source venv/Scripts/activate` : fichier introuvable | Sous macOS et Linux, le chemin est `venv/bin/activate` | Adapter le chemin au système |
| `pip install` semble réussir, l'import échoue ensuite | Le `venv` n'était pas activé : les paquets sont partis dans le Python global | Réactiver, revérifier `sys.prefix`, réinstaller |
