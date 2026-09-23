# Version >= à celle du venv local : requirements.txt fige des paquets compilés
# pour une version précise de Python (pip échoue au build sinon).
FROM python:3.14-slim

# Un utilisateur sans privilège, créé tôt : cette couche ne change jamais et
# reste en cache. Par défaut un container tourne en root — si un attaquant
# sort de l'application, il est root dans le container, à une évasion près
# de l'être sur le nœud.
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

# Copié en premier : ce fichier change rarement. Docker met cette couche
# en cache et ne relance pip install que si requirements.txt change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copié en dernier : le code change à chaque itération, sans invalider
# le cache de la couche pip install ci-dessus.
COPY src/ src/
COPY models/ models/

ENV PYTHONPATH=/app/src

# Le manifeste Kubernetes monte un rootfs en lecture seule. Deux consequences :
# - Python ne doit pas essayer d'ecrire des .pyc a l'import ;
# - HOME doit pointer vers un chemin inscriptible (un volume emptyDir).
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOME=/tmp

# Seul chemin ou l'application ecrit en production : le journal des
# predictions (Ch. 15). Cree ici pour que le point de montage existe.
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Tout ce qui suit s'execute sans privilege.
USER appuser

EXPOSE 8000

# --host 0.0.0.0 est obligatoire : sans lui uvicorn n'écoute que sur la boucle
# locale DU CONTAINER, et le mapping -p 8000:8000 ne mène nulle part.
CMD ["uvicorn", "churn_predictor.app:app", "--host", "0.0.0.0", "--port", "8000"]
