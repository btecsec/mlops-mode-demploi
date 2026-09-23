# Chapitre 16 — Sécurité et gouvernance

L'auditeur pose deux questions : « prouvez-moi que ce client n'apparaît plus
nulle part » et « qui a consulté ses prédictions cette année ». Ce chapitre
construit les réponses — et il fallait les construire **avant** la question.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `src/churn_predictor/privacy.py` | `pseudonymize()` : SHA-256 salé, stable, irréversible |
| `src/churn_predictor/audit.py` | Une ligne par prédiction : qui, quand, quel client, quelle version |
| `src/churn_predictor/config.py` | `AUDIT_LOG`, fichier distinct du journal de drift |
| `src/churn_predictor/app.py` | En-têtes `X-Customer-Id` et `X-Caller`, audit branché sur `/predict` |
| `iam/policy-readonly-registry.json` | Moindre privilège : une action, une ressource |
| `scripts/rollback_model.py` | Redéplace l'alias `champion`, sans rien supprimer |
| `.env.example` | Le sel de pseudonymisation, jamais commité |
| `tests/test_privacy.py` + `conftest.py` | 15 tests |

## Deux journaux, pas un

Le journal du Chapitre 15 enregistre des **features** : il sert à mesurer la
dérive. Celui-ci enregistre une **responsabilité** : il sert à un auditeur.

Les mélanger reviendrait à donner à l'équipe data un accès permanent aux traces
d'accès, et à l'auditeur un fichier illisible. Deux publics, deux politiques de
rétention, deux fichiers.

```text
logs/predictions_log.csv   → features + probabilité          (Ch. 15, drift)
logs/audit_log.csv         → caller + hash + version + date  (Ch. 16, audit)
```

Un test vérifie qu'aucun identifiant, même pseudonymisé, ne fuit du second vers
le premier.

## L'identité vient de l'en-tête, pas du corps

```python
def predict(
    features: CustomerFeatures,
    x_customer_id: str = Header(default="anonymous"),
    x_caller: str = Header(default="unknown"),
):
```

Le schéma du Chapitre 5 ne change pas d'une ligne. L'identité est posée par la
passerelle ou le service appelant, comme une clé d'API — le modèle n'a donc
aucun moyen d'apprendre sur un identifiant client, et les tests des chapitres
précédents continuent de passer sans en-tête.

## Le sel n'a pas de valeur par défaut

```python
PSEUDONYM_SALT = os.environ["PSEUDONYM_SALT"]
```

Volontairement. Un sel par défaut serait partagé par toutes les installations :
les empreintes deviendraient comparables entre elles, donc ré-identifiables par
recoupement. Mieux vaut un démarrage qui échoue bruyamment.

En local :

```bash
cp .env.example .env
export PSEUDONYM_SALT="$(openssl rand -hex 32)"
```

En production, il vient du Secret Kubernetes du Chapitre 12 :

```bash
kubectl create secret generic churn-api-secret \
  --from-literal=PSEUDONYM_SALT="$(openssl rand -hex 32)"
```

Les tests, eux, posent un sel constant dans `tests/conftest.py` — avant tout
import, seul endroit possible puisque `privacy.py` lit la variable à l'import.
C'est acceptable là, et seulement là : un sel reproductible rend les empreintes
comparables d'un run à l'autre, ce qui est exactement le défaut à éviter en
production.

## Lancer la solution

```bash
python ../../bootstrap.py 15
cd solution
pip install -r requirements.txt && pip install -e .
export PSEUDONYM_SALT="$(openssl rand -hex 32)"
python -m churn_predictor.train
python -m churn_predictor.register

pytest -v      # 112 tests + 2 skips (ch. 1 à 12)
```

Une prédiction tracée de bout en bout :

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-Customer-Id: 7590-VHVEG" \
  -H "X-Caller: crm-batch" \
  -d @../tests/payload_exemple.json

cat logs/audit_log.csv
```

```text
timestamp,caller,customer_hash,model_version,probability
2026-08-28T18:04:11.923847+00:00,crm-batch,3f2a91c4e7b60d18,1,0.62
```

Quatre questions, une ligne, et jamais `7590-VHVEG`.

## Rollback : deux niveaux, deux commandes

Le modèle :

```bash
python scripts/rollback_model.py --list
python scripts/rollback_model.py --version 4
```

```text
Alias 'champion' déplacé de v5 vers v4.
Pour annuler ce rollback : --version 5
```

`set_registered_model_alias` déplace un pointeur, il ne supprime rien. La
version quittée reste consultable par son numéro — le rollback est lui-même
réversible, ce qui compte quand on se trompe de numéro sous pression.

Le déploiement (Chapitre 12) :

```bash
kubectl rollout history deployment/churn-api
kubectl rollout undo deployment/churn-api --to-revision=2
```

```text
deployment.apps/churn-api rolled back
```

## Une ligne d'audit vaut mieux qu'une ligne parfaite

`get_champion_version()` écrit `unknown` si le Registry est injoignable, au lieu
de lever. Perdre la trace d'une prédiction est irréversible ; perdre son numéro
de version ne l'est pas — le run MLflow, lui, reste retrouvable par horodatage.

La fonction est en `lru_cache` : la version du champion ne change qu'au moment
d'une promotion (Chapitre 11), donc au redémarrage du service. Interroger le
Registry à chaque requête coûterait un aller-retour réseau par prédiction.

## Le piège du chapitre

Journaliser le `customerID` en clair « juste pour déboguer », en se promettant
de retirer la ligne avant la production. Une fois qu'un identifiant en clair a
atterri dans un log, il y reste : sauvegardes, exports, outils de monitoring
tiers.

La pseudonymisation est la valeur par défaut du code, jamais une étape ajoutée
plus tard. `test_l_identifiant_client_n_apparait_jamais_en_clair` est là pour
que la promesse ne dépende pas de la mémoire de quelqu'un.

## Le piège de `"Resource": "*"`

La policy IAM autorise une action (`sagemaker:InvokeEndpoint`) sur une ressource
précise (l'endpoint du Chapitre 14). Remplacer la ressource par `*` est la
façon la plus courante de transformer un droit d'invocation en droit sur tout
le compte cloud — et ça ne produit aucune erreur, jamais.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `KeyError: 'PSEUDONYM_SALT'` à l'import | Le sel n'est pas dans l'environnement. C'est voulu : pas de valeur par défaut | L'exporter (Étape 1), et le mettre au Secret pour le cluster |
| Pod en `CreateContainerConfigError` | Le Secret ne porte pas encore la clé `PSEUDONYM_SALT` | Le remplacer par la version à deux clés de l'Étape 1 |
| Pod `Running`, probes vertes, `audit_log.csv` vide | `fsGroup` oublié : l'`emptyDir` est monté `root:root`, l'uid 10001 ne peut pas y écrire | Le remettre dans le `securityContext` du Pod |
| `container has runAsNonRoot and image will run as root` | L'image déployée est antérieure au `USER appuser` | Reconstruire, redéployer au nouveau SHA |
| `Registered Model with name=churn-predictor not found` | `set_tracking_uri` absent, ou Registry vide | La ligne en tête d'`audit.py` ; sinon, Chapitre 7 |
