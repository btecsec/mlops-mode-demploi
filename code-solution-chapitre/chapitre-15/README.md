# Chapitre 15 — Monitoring et observabilité : détecter le drift

Deux couches, deux questions différentes. La Couche 1 dit « le service
fonctionne ». Seule la Couche 2 dit « le service répond juste ».

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `src/churn_predictor/app.py` | `Instrumentator` → `/metrics`, `log_prediction()` branchée dans `/predict` |
| `src/churn_predictor/config.py` | `PREDICTIONS_LOG`, ancré sur `ROOT_DIR` |
| `monitoring/docker-compose.yml` | Prometheus + Grafana |
| `monitoring/prometheus.yml` | Scrape de `host.docker.internal:8000` (l'API instrumentée, lancée en local) |
| `monitoring/check_drift.py` | Comparaison Evidently baseline vs production |
| `airflow/dags/churn_retrain_dag.py` | `@task.branch` : ré-entraînement conditionné au drift |
| `pyproject.toml` | `monitoring/` devient un paquet installable |
| `.gitignore` | `logs/` — de la donnée de production, jamais du code |
| `tests/test_check_drift.py` | 12 tests |

## Couche 1 : la santé technique

```python
Instrumentator().instrument(app).expose(app)   # ajoute GET /metrics
```

Une ligne, et Prometheus a de quoi lire : latence, volume de requêtes, codes de
retour. Aucune instrumentation manuelle.

```bash
cd monitoring && docker compose up -d
```

Grafana répond sur <http://localhost:3000>, Prometheus sur
<http://localhost:9090>.

Grafana demande un identifiant. Le `docker-compose.yml` n'en fixe aucun :
l'image garde ceux d'usine, `admin` / `admin`, puis réclame un nouveau mot de
passe (*Skip* passe outre, acceptable en local seulement). Pour le fixer,
deux variables dans le service `grafana`, la seconde lue dans un `.env` jamais
commité :

```yaml
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
```

Le dashboard est vide tant qu'aucune requête n'a traversé l'API : un compteur
qui n'a rien compté ne publie aucune série, et Grafana affiche *No data*.
Générez du trafic, `client.json` étant le payload du Chapitre 10.

```bash
curl -s http://localhost:8000/health

for i in $(seq 1 60); do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "@client.json" > /dev/null
  sleep 1
done
```

```powershell
1..60 | ForEach-Object {
  curl.exe -s -X POST http://localhost:8000/predict `
    -H "Content-Type: application/json" `
    -d "@client.json" | Out-Null
  Start-Sleep -Seconds 1
}
```

Lancez-la depuis la racine du projet, pas depuis `monitoring/` : `@client.json`
est un chemin relatif au dossier courant, et `curl` échoue alors sur un message
qui ne nomme ni le fichier ni le dossier où il l'a cherché.

```text
curl: option -d: error encountered when reading a file
```

Prometheus scrute toutes les 15 secondes : comptez une demi-minute avant la
première courbe. Dans Grafana, la source de données Prometheus s'adresse par
`http://prometheus:9090` — le nom du service compose ; depuis le container
Grafana, `localhost` désigne Grafana lui-même.

Le panneau se crée par *Dashboards* → *New* → *New dashboard* →
*+ Add visualization*. Dans la zone de requête, basculez de *Builder* à *Code* :
sans ça, pas de champ où coller du PromQL.

Deux panneaux, pas un seul — un débit en requêtes par seconde et une latence en
secondes ne partagent pas un axe. L'unité se règle à droite, section
*Standard options*, champ *Unit*.

Panneau « Débit », unité `requests/sec` :

```text
rate(http_requests_total{handler="/predict"}[1m])
```

Panneau « Latence p95 », unité `seconds (s)` :

```text
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{handler="/predict"}[5m]))
```

Le premier dit combien d'appels arrivent, le second sous quel délai 95% d'entre
eux se terminent.

Prometheus tourne dans un container, hors du cluster. La cible est donc
`host.docker.internal:8000` — la machine hôte vue depuis un container — et sur
ce port doit tourner l'API instrumentée, lancée en local dans un second
terminal.

```bash
uvicorn churn_predictor.app:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` compte : sans lui, uvicorn n'écoute que sur `127.0.0.1`, et
Prometheus, qui frappe à l'adresse de la machine hôte, trouve porte close. Sous
Docker Desktop le trafic est réacheminé vers la boucle locale et cela passe
quand même ; sous Linux, où `host.docker.internal` est la passerelle `docker0`,
cela échoue.

Ces deux adresses ne se valent pas selon d'où on les écrit.
`host.docker.internal` désigne la machine hôte **vue depuis un container** ;
collée dans le navigateur du poste, elle pointe sur l'adresse de celui-ci dans
le réseau local, d'où le « site inaccessible ». Pour un contrôle manuel,
`http://localhost:8000/metrics`.

Pas le Pod du Chapitre 12 : son image a été construite avant la ligne
`Instrumentator()`. Une image est un instantané du code, pas un lien vers lui —
le Pod répond `404` sur `/metrics`, et le journal de prédictions de la Couche 2
s'écrirait dans le container, hors de portée de `check_drift.py`. Déployé
*dans* le cluster, Prometheus viserait directement `churn-api-service:80`.

Une page dit si la collecte fonctionne : `http://localhost:9090/targets`. Le
job `churn-api` doit y être **UP**.

```text
churn-api   DOWN   server returned HTTP status 404 Not Found
```

`404` : l'API répond sans exposer `/metrics` — processus lancé avant
l'instrumentation, ou Pod du cluster. `connection refused` : rien n'écoute sur
le port 8000. Dans les deux cas Grafana affichera *No data*, sans erreur.

## Couche 2 : la santé statistique

Un modèle qui se trompe ne lève aucune exception. Il répond, avec confiance, une
prédiction moins bonne qu'avant. Et la vraie réponse — « ce client est-il
vraiment parti ? » — n'arrive que des semaines plus tard.

D'où le journal. Chaque `/predict` écrit sa ligne dans
`logs/predictions_log.csv`, et `check_drift.py` compare ce journal au dataset
d'entraînement du Chapitre 3.

```bash
python monitoring/check_drift.py
```

```text
Part de colonnes dérivées : 0%
```

Zéro dérive au départ, et c'est normal : le trafic de test vient du dataset qui
sert justement de baseline. Ce chiffre n'a d'intérêt que dans la durée.

## Lancer la solution

```bash
python ../../bootstrap.py 14
cd solution
pip install -r requirements.txt && pip install -e .
python -m churn_predictor.train

pytest -v      # 97 tests + 2 skips (ch. 1 à 11)
```

Puis, pour mesurer un drift réel. L'ordre compte, et c'est celui du livre :
les dépendances d'abord, le code ensuite, le lancement en dernier. Un
processus Python charge ses modules au démarrage et ne les relit jamais parce
qu'un fichier a changé sur le disque.

```bash
pip install -r requirements-monitoring.txt
uvicorn churn_predictor.app:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` parce que Prometheus frappe à l'adresse de la machine hôte, pas
sur la boucle locale. Ce terminal reste ouvert : c'est le Terminal A du livre.

```bash
# 200 vraies lignes du dataset envoyées à l'API, pour alimenter le journal
python -c "
import json, urllib.request
from churn_predictor.data import load_raw_data

df = load_raw_data().drop(columns=['customerID', 'Churn'])
df = df[df['TotalCharges'].str.strip() != '']   # 11 lignes vides dans le CSV brut

for row in df.sample(200, random_state=42).to_dict(orient='records'):
    req = urllib.request.Request(
        'http://localhost:8000/predict',
        data=json.dumps(row).encode(),
        headers={'Content-Type': 'application/json'},
    )
    urllib.request.urlopen(req).read()
"
python monitoring/check_drift.py
```

## Evidently 0.7 a refondu son API

`requirements-monitoring.txt` épingle `evidently==0.7.21`, et `check_drift.py`
cible cette API-là. Ce qui a changé :

| Avant la 0.7 | Depuis la 0.7 |
| --- | --- |
| `from evidently.report import Report` | `from evidently import Report` |
| `from evidently.metric_preset import DataDriftPreset` | `from evidently.presets import DataDriftPreset` |
| `report.run(...)` remplit le rapport | `report.run(...)` rend un `Snapshot` |
| `report.as_dict()[...]["result"]["share_of_drifted_columns"]` | `snapshot.dict()[...]["value"]["share"]` |

Aucun shim de compatibilité : un `pip install evidently` sans numéro de version
attrape la dernière publiée et le script s'arrête sur
`ModuleNotFoundError: No module named 'evidently.report'`. Et `evidently.report`
n'est pas un paquet séparé — `pip install evidently.report` ne répare rien.

Bonne nouvelle au passage : la 0.7 s'installe sur Python 3.13 et 3.14. L'ancien
plafond `<0.5` tirait `numpy<2.1`, sans wheel au-delà de la 3.12, et `pip`
tentait alors de compiler numpy depuis les sources. Les deux tests qui appellent
réellement Evidently restent en **skip** si Evidently n'est pas installé, plutôt
que de rendre la suite rouge sur une contrainte d'environnement.

## Trois détails qui coûtent une soirée

**Uvicorn ne relit pas `app.py`.** C'est la raison pour laquelle le TP du livre
écrit tout le code de l'Étape 2 avant de lancer quoi que ce soit à l'Étape 3.
Dans l'ordre inverse, le processus tourne sur le code chargé à son démarrage :
`/predict` répond `200`, `logs/` reste vide, et `check_drift.py` s'arrête sur
« Journal de prédictions introuvable » — un message qui accuse le trafic alors
que le coupable est le processus. Même leçon que l'image du Pod ci-dessus, à
l'échelle d'un simple processus. En développement, `--reload` relance le serveur
à chaque frappe et masque le problème ; en production, rien ne le masque.

**`monitoring/` n'est qu'un dossier.** Le DAG l'importe
(`from monitoring.check_drift import ...`), et sans packaging Python ne le voit
pas : `ModuleNotFoundError: No module named 'monitoring'`, la même leçon qu'au
Chapitre 4. D'où le `__init__.py` et le `pyproject.toml` élargi :

```toml
[tool.setuptools.packages.find]
where = ["src", "."]
include = ["churn_predictor*", "monitoring*"]
```

**Le nettoyage de `TotalCharges`.** La baseline le subit à l'entraînement, le
journal contient déjà des nombres. Sans le `to_numeric` dans `load_baseline()`,
la même colonne est comparée en texte d'un côté et en nombre de l'autre :
Evidently choisit deux tests statistiques différents et annonce une dérive qui
n'existe pas.

## Le DAG ne réentraîne plus systématiquement

```python
@task.branch
def should_retrain() -> str:
    from monitoring.check_drift import DRIFT_THRESHOLD, check_drift
    return "train_challenger" if check_drift() > DRIFT_THRESHOLD else "skip_retrain"
```

Le calendrier dit *quand regarder*, le drift dit *s'il y a lieu d'agir*. La
branche `skip_retrain` est une tâche explicite, pas un chemin mort : dans
l'interface Airflow, on voit que le DAG a tourné et **décidé**, au lieu de se
demander s'il a planté.

L'import d'Evidently est local à la fonction. Le scheduler parse ce fichier
toutes les quelques secondes pour découvrir les DAG : charger Evidently à chaque
passage ralentirait tout, et une erreur d'import ferait disparaître le DAG
entier de l'interface.

## Le piège du chapitre

Monitorer uniquement la Couche 1 et déclarer le système « sous contrôle ».
C'est exactement l'incident d'ouverture du Chapitre 1 : un dashboard
intégralement vert, un modèle faux depuis trois jours, et rien dans l'outillage
pour le révéler.

Un camion qui roule parfaitement, à pleine vitesse, dans le mauvais sens n'est
pas moins dangereux qu'un camion en panne. Il est pire — personne ne s'arrête
pour vérifier.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `logs/` reste vide, `/predict` répond `200` | L'API tourne sur le code d'avant l'Étape 2 | Ctrl+C dans le Terminal A, relancer `uvicorn` |
| Cible `DOWN`, `404 Not Found` | Le port 8000 est tenu par autre chose que votre API — souvent un `kubectl port-forward` du Ch. 12, dont l'image est antérieure à l'Étape 2 | Arrêter le tunnel, relancer l'API en local |
| Cible `DOWN`, `connection refused` | Rien n'écoute sur le port 8000, ou uvicorn a été lancé sans `--host 0.0.0.0` | Relancer avec le drapeau |
| `curl: option -d: error encountered when reading a file` | La boucle tourne depuis `monitoring/`, où `client.json` n'existe pas | `cd ..` avant la boucle |
| Grafana affiche *No data* | Aucune série n'existe encore, ou la collecte ne passe pas | Vérifier `http://localhost:9090/targets` avant de soupçonner Grafana |
| `host.docker.internal` inaccessible au navigateur | Ce nom désigne l'hôte **vu depuis un container**, pas depuis votre poste | Pour un contrôle à la main, prendre `http://localhost:8000/metrics` |
| `ModuleNotFoundError: No module named 'monitoring'` | `pip install -e .` n'a pas été rejoué après l'Étape 8 | Le relancer depuis la racine |
