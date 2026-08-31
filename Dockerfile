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

CMD ["uvicorn", "churn_predictor.app:app", "--host", "0.0.0.0", "--port", "8000"]
