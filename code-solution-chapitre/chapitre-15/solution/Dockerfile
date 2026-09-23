# Version >= à celle du venv local : requirements.txt fige des paquets compilés
# pour une version précise de Python (pip échoue au build sinon).
FROM python:3.14-slim

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

EXPOSE 8000

# --host 0.0.0.0 est obligatoire : sans lui uvicorn n'écoute que sur la boucle
# locale DU CONTAINER, et le mapping -p 8000:8000 ne mène nulle part.
CMD ["uvicorn", "churn_predictor.app:app", "--host", "0.0.0.0", "--port", "8000"]
