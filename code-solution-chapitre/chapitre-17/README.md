# Chapitre 17 — Portfolio MLOps et ouverture LLMOps

Deux candidats ont suivi le même parcours. Le premier écrit « projet MLOps,
tutoriel suivi » sur son CV. Le second montre un dépôt avec un badge CI vert,
un lien de démo et un historique Git de dix-sept chapitres. Un seul obtient
l'entretien technique.

Ce chapitre transforme les quinze précédents en preuve, puis ouvre sur le
LLMOps — même discipline, nouvel objet.

## Ce que le chapitre ajoute

| Fichier | Rôle |
|----|----|
| `src/churn_predictor/explain.py` | `explain_prediction()` : traduit une probabilité en explication pour un agent |
| `src/churn_predictor/judge.py` | `judge_explanation()` : un second LLM note la sortie du premier |
| `src/churn_predictor/predict_explain_judge.py` | Enchaîne les trois briques : prédiction, explication, jugement |
| `requirements-llm.txt` | Dépendances LLM, séparées du pipeline de churn |
| `.env.example` | `OPENROUTER_API_KEY` — la clé vit dans l'environnement, jamais dans le code |
| `tests/test_explain.py` | Teste les deux chaînes **sans** appeler de LLM ni consommer de jeton |

Le reste de `solution/` est l'état complet laissé par le Chapitre 16 : API,
Docker, MLflow, DVC, CI/CD, Airflow, Kubernetes, Terraform, monitoring,
gouvernance.

## MLOps → LLMOps : les équivalences

| Ce livre | Transposition LLMOps |
|----|----|
| MLflow Tracking / Registry (Ch. 7) | Tracer les prompts et les versions de modèle |
| Airflow, champion/challenger (Ch. 11) | LLM-as-a-judge : un LLM évalue la sortie d'un autre |
| Kubernetes, HPA (Ch. 12) | vLLM : serving optimisé de LLM à grande échelle |
| Evidently, drift (Ch. 15) | Dérive de la qualité des réponses générées |

## Pourquoi OpenRouter

OpenRouter est une passerelle : une seule clé et une seule facture donnent
accès aux modèles d'OpenAI, d'Anthropic, de Mistral, de Google et de dizaines
d'autres. Changer de modèle revient à changer la constante `MODEL` d'
`explain.py` — le jour où le vôtre double de prix ou disparaît, il n'y a pas
une ligne de code à réécrire.

La passerelle parle le protocole de l'API OpenAI. `langchain-openai` convient
donc tel quel ; seules l'adresse du serveur (`BASE_URL`) et la forme de
l'identifiant de modèle changent. Sur OpenRouter, un modèle se nomme
`fournisseur/modèle` : `openai/gpt-4o-mini`, jamais `gpt-4o-mini`. Un
identifiant sans préfixe part en `404`.

Un piège pour la fin : `ChatOpenAI` va chercher `OPENAI_API_KEY` tout seul
dans l'environnement, mais **pas** `OPENROUTER_API_KEY`. Il faut la lui
passer. `get_llm()` la lit avec `os.environ[...]` et non `.get()` : une clé
absente doit lever un `KeyError` ici, pas partir en requête anonyme rejetée en
`401` quelques couches plus loin.

## Lancer la solution

```bash
python ../../bootstrap.py 16
cd solution
python -m venv venv
source venv/Scripts/activate      # PowerShell : venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-llm.txt
pip install -e .

cp .env.example .env                    # puis renseigner OPENROUTER_API_KEY
# PowerShell : $env:OPENROUTER_API_KEY = "sk-or-v1-..."
export OPENROUTER_API_KEY="sk-or-v1-..."

python -m churn_predictor.predict_explain_judge
```

À lancer depuis la racine de `solution/` : `client.json` est lu par chemin
relatif au dossier de travail.

## Voir les traces (optionnel)

`pip install langsmith`, puis trois variables d'environnement avant de relancer :
`LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=lsv2_...` et
`LANGSMITH_PROJECT=churn-llmops`. Chaque appel de LLM apparaît alors sur
smith.langchain.com avec son prompt substitué, sa réponse brute, sa latence et
son coût. La sortie console, elle, ne change pas.

## Résultat attendu

```text
Ce client est à risque élevé : contrat sans engagement et seulement 3 mois
d'ancienneté, deux facteurs qui pèsent lourd dans le désabonnement.
Proposez-lui une offre d'engagement 12 mois avec avantage tarifaire.
note du juge : 4
```

La formulation exacte varie d'un appel à l'autre — c'est justement pour ça
qu'on ne teste jamais un LLM en comparant sa réponse à une chaîne fixe.

## Lancer les tests

```bash
pytest -v
```

`test_explain.py` injecte un faux LLM (`RunnableLambda`) à la place du vrai :
il vérifie que le prompt reçu contient bien les bonnes variables et que le
parsing de la note résiste à `"4/5"` ou `"Note : 4"`. **Aucun appel réseau,
aucun jeton facturé.** Un test qui appelle un vrai LLM est lent, non
déterministe et coûteux à chaque exécution en CI — ce n'est pas un test.

Sans `langchain-core` installé, ces tests sont ignorés proprement
(`pytest.importorskip`) plutôt que de faire échouer toute la suite.

## Le détail qui coince toujours

`judge_explanation()` n'utilise pas `int(raw)`. Un LLM finit toujours par
répondre « 4/5 » ou « Note : 4 » malgré la consigne, et un `int()` direct casse
la production sur une réponse parfaitement raisonnable. On extrait le chiffre
par expression régulière, et on lève une erreur explicite quand il n'y en a
pas — même réflexe que la validation Pydantic du Chapitre 5, appliqué à une
sortie de LLM.

## Si ça ne marche pas

Les pannes rencontrées à ce TP, dans l'ordre où elles se déclarent. Le livre ne les déroule pas : elles vivent ici, à côté du code qui les provoque.

| Symptôme | Cause | Correctif |
|----|----|----|
| `KeyError: 'OPENROUTER_API_KEY'` | La clé n'est pas dans l'environnement de **ce** terminal | La ré-exporter : un `export` meurt avec le terminal |
| `AuthenticationError: Error code: 401` | La clé est présente mais révoquée, ou copiée avec un espace | En regénérer une sur OpenRouter |
| `APIStatusError: Error code: 402` | Le compte OpenRouter n'a plus de crédit | Utiliser un modèle suffixé `:free` (comme Llama 3) pour contourner ce blocage |
| `NotFoundError: Error code: 404` | L'identifiant du modèle a perdu son préfixe de fournisseur | `meta-llama/llama-3-8b-instruct:free`, jamais `llama-3-8b-instruct:free` |
| `Note illisible renvoyée par le juge` | Le LLM a répondu autre chose qu'un chiffre malgré la consigne | Rien à corriger : c'est le comportement voulu, l'erreur vaut mieux qu'une note devinée |
| Le badge CI affiche `no status` | L'URL du badge ne désigne pas le bon fichier de workflow | Aligner le nom sur `ci.yml` du Chapitre 10 |
