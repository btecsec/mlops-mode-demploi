# Exercice — Chapitre 17

**Starter fourni** : l'état exact laissé par `chapitre-16` — pipeline complet,
surveillé et gouverné, du notebook à la production.

**Objectif** : rendre ce travail lisible par un recruteur en moins de deux
minutes, puis brancher un premier assistant LLM avec la même rigueur que le
reste du livre.

## À faire, sans regarder `solution/`

1. Écrire le `README.md` racine du projet : badge CI, lien de démo, schéma
   d'architecture, puis seulement ensuite le détail technique.
2. Installer `langchain-core` et `langchain-openai` dans un
   `requirements-llm.txt` séparé, et documenter `OPENROUTER_API_KEY` dans
   `.env.example`. Le client vise OpenRouter : `base_url` sur
   `https://openrouter.ai/api/v1`, et la clé passée explicitement.
3. Écrire `src/churn_predictor/explain.py` : un `ChatPromptTemplate` qui
   transforme une probabilité de churn et deux features en une phrase
   actionnable pour un agent de centre d'appel.
4. Écrire `src/churn_predictor/judge.py` : un second appel LLM qui note de 1 à 5
   la clarté de l'explication produite.
5. Rendre le LLM **injectable** dans les deux fonctions, pour pouvoir les tester
   sans appel réseau.
6. Écrire `tests/test_explain.py` avec un faux LLM (`RunnableLambda`) : aucun
   jeton consommé, aucun test non déterministe.

## Questions guidées

1. Pourquoi le badge CI et le lien de démo doivent-ils apparaître **avant** le
   détail technique dans le README racine ?
2. En quoi `EXPLAIN_PROMPT | llm` est-il la même idée de composition que le
   `Pipeline` scikit-learn du Chapitre 3 ?
3. Pourquoi la clé d'API ne doit-elle jamais apparaître dans `explain.py`, même
   dans un dépôt privé ? *(indice : Chapitre 16)*
4. Le LLM-as-a-judge reprend quel principe exact du Chapitre 11 ?
5. Pourquoi `int(raw)` est-il un bug en attente dans `judge_explanation()` ?
   Donnez deux réponses de LLM parfaitement raisonnables qui le feraient planter.
6. Pourquoi un test qui appelle réellement l'API d'un LLM n'est-il pas un
   test ? Citez trois raisons.
7. À quoi servirait vLLM ici, et à quelle brique de ce livre correspond-il ?
8. Vous versionnez désormais du code, des données et des modèles. Que faudrait-il
   versionner en plus dans un projet LLMOps ?

## Critères de réussite

- Le README racine tient sur un écran et prouve trois choses : ça tourne, c'est
  compris, c'est testé.
- `explain_prediction()` et `judge_explanation()` acceptent un `llm` injecté.
- `pytest -v` passe sans clé d'API et sans accès réseau.
- Sans `langchain-core` installé, les tests LLM sont ignorés, pas en échec.
- `git log --oneline` raconte seize chapitres de manière lisible.

## Piège de ce chapitre

Lister ChatGPT, LangChain, Docker, Kubernetes et Terraform sur un CV sans aucun
lien vers un projet qui les utilise réellement. Un recruteur technique reconnaît
immédiatement une liste de mots-clés copiée d'une offre d'emploi, et la
sanctionne — elle ne prouve rien. Chaque techno citée doit pointer vers du code
qui tourne.
