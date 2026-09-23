"""Installe le jeu de données du fil rouge dans le chapitre demandé.

Le CSV Telco Customer Churn n'est jamais commité (piège classique du Chapitre 4).
Ce script le copie depuis `data/raw/` vers `chapitre-XX/solution/data/raw/`, seul
endroit où `churn_predictor.config.DATA_PATH` va le chercher.

Usage :
    python bootstrap.py 3        # un chapitre
    python bootstrap.py all      # tous les chapitres qui en ont besoin
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_NAME = "WA_Fn-UseC_-Telco-Customer-Churn.csv"
SOURCE = ROOT / "data" / "raw" / CSV_NAME

# Le Chapitre 3 lit le CSV depuis data/ (pas encore data/raw/) : il a sa propre cible.
# Les Chapitres 1 et 2 ne touchent pas au dataset : ils n'ont pas de cible.
CHAPTER_TARGETS = {3: "data", **{n: "data/raw" for n in range(4, 18)}}


def install(chapter: int) -> None:
    if chapter not in CHAPTER_TARGETS:
        raise SystemExit(
            f"Le Chapitre {chapter} n'utilise pas le dataset "
            f"(chapitres attendus : {sorted(CHAPTER_TARGETS)})"
        )
    target_dir = ROOT / f"chapitre-{chapter:02d}" / "solution" / CHAPTER_TARGETS[chapter]
    if not target_dir.parent.parent.exists():
        raise SystemExit(f"Chapitre inconnu : {chapter}")
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, target_dir / CSV_NAME)
    print(f"CSV installé dans {target_dir.relative_to(ROOT)}")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(
            f"{SOURCE.relative_to(ROOT)} introuvable — voir data/raw/README.md "
            "pour le télécharger depuis Kaggle."
        )
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)

    arg = sys.argv[1]
    chapters = sorted(CHAPTER_TARGETS) if arg == "all" else [int(arg)]
    for chapter in chapters:
        install(chapter)


if __name__ == "__main__":
    main()
