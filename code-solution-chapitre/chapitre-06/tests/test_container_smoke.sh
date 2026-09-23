#!/usr/bin/env bash
# Smoke test du Chapitre 6 : build, run, curl /health et /predict, nettoyage.
# Lancer depuis chapitre-06/solution/ :  bash ../tests/test_container_smoke.sh
set -euo pipefail

IMAGE="churn-api:0.1"
NAME="churn-api-smoke"
PORT=8001                      # 8001 et pas 8000 : ne rentre pas en conflit
                               # avec un uvicorn lancé à la main à côté.

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "--- 1/4 prérequis : le build embarque le modèle, il ne l'entraîne pas"
[ -f models/churn_model.pkl ] || python -m churn_predictor.train

echo "--- 2/4 build"
docker build -t "$IMAGE" .

echo "--- 3/4 run"
cleanup
docker run -d -p "$PORT:8000" --name "$NAME" "$IMAGE" >/dev/null

# L'API charge le modèle au premier appel : on laisse le temps au container.
for i in $(seq 1 30); do
  if curl -sf "http://localhost:$PORT/health" >/dev/null; then break; fi
  [ "$i" = 30 ] && { echo "KO: /health ne répond pas"; docker logs "$NAME"; exit 1; }
  sleep 1
done

echo "--- 4/4 vérifications"
health=$(curl -sf "http://localhost:$PORT/health")
[ "$health" = '{"status":"ok"}' ] || { echo "KO: /health -> $health"; exit 1; }

proba=$(curl -sf -X POST "http://localhost:$PORT/predict" \
  -H "Content-Type: application/json" \
  -d @../tests/payload_exemple.json | python -c "import json,sys; print(json.load(sys.stdin)['probability'])")

# Même modèle, même payload qu'au Chapitre 5 : la valeur doit être identique.
[ "$proba" = "0.735" ] || { echo "KO: probability attendue 0.735, obtenue $proba"; exit 1; }

echo "OK: /health et /predict répondent depuis l'hôte, probability = $proba"
