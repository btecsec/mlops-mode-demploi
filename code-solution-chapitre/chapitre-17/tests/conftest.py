"""Configuration commune aux tests du Chapitre 16.

`privacy.py` lit `PSEUDONYM_SALT` à l'import et échoue bruyamment s'il est
absent — c'est voulu (voir le module). Les tests fournissent donc un sel de
test, posé **avant** tout import de `churn_predictor` : conftest.py est chargé
par pytest avant les modules de test, ce qui en fait le seul endroit possible.

Un sel de test constant est acceptable ici, et seulement ici : il rend les
empreintes reproductibles d'un run à l'autre. En production, c'est exactement
ce qu'il ne faut pas — d'où le `openssl rand -hex 32` du .env.example.
"""

import os

os.environ.setdefault("PSEUDONYM_SALT", "sel-de-test-jamais-utilise-en-production")
