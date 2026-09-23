import hashlib
import os

# Sel stocké en Secret Kubernetes (Ch. 12), injecté dans l'environnement.
# Pas de valeur par défaut, volontairement : mieux vaut un démarrage qui
# échoue bruyamment qu'un sel partagé par tout le monde, qui rendrait les
# empreintes comparables d'une installation à l'autre.
PSEUDONYM_SALT = os.environ["PSEUDONYM_SALT"]


def pseudonymize(customer_id: str) -> str:
    """Transforme un identifiant client en empreinte irréversible,
    stable (le même client donne toujours la même empreinte, utile
    pour le suivi), mais qui ne permet jamais de retrouver l'identité."""
    return hashlib.sha256(f"{customer_id}{PSEUDONYM_SALT}".encode()).hexdigest()[:16]
