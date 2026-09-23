"""Pseudonymisation des identifiants clients.

Un identifiant client en clair qui atterrit dans un fichier de log y reste :
dans les sauvegardes, dans les exports, chez l'outil de monitoring tiers. La
pseudonymisation est donc la valeur par défaut du code, jamais une étape
ajoutée « plus tard, avant la prod ».
"""

import hashlib
import os

# Sel stocké en Secret Kubernetes (Ch. 12), injecté dans l'environnement.
# Pas de valeur par défaut, volontairement : mieux vaut un démarrage qui échoue
# bruyamment qu'un sel partagé par tout le monde, qui rendrait les empreintes
# comparables — et donc ré-identifiables par recoupement — d'une installation
# à l'autre.
PSEUDONYM_SALT = os.environ["PSEUDONYM_SALT"]

# 16 caractères hexadécimaux = 64 bits : assez pour ne pas collisionner sur des
# millions de clients, assez court pour rester lisible dans un journal.
LONGUEUR_EMPREINTE = 16


def pseudonymize(customer_id: str) -> str:
    """Transforme un identifiant client en empreinte irréversible.

    Stable — le même client donne toujours la même empreinte, ce qui permet de
    recouper deux requêtes — mais qui ne permet jamais de remonter à l'identité
    réelle : SHA-256 n'est pas réversible par conception, et le sel interdit
    l'attaque par dictionnaire sur un espace d'identifiants aussi petit que
    celui du dataset Telco.
    """
    empreinte = hashlib.sha256(f"{customer_id}{PSEUDONYM_SALT}".encode())
    return empreinte.hexdigest()[:LONGUEUR_EMPREINTE]
