"""Traduit une prédiction de churn en explication utile à un agent.

Le LLM n'entraîne rien et ne prédit rien : le RandomForest du Chapitre 5 reste
seul responsable du chiffre. Le LLM habille ce chiffre en une phrase
actionnable — la frontière entre les deux est le point important du chapitre.

Prérequis :
    pip install -r requirements-llm.txt
    export OPENROUTER_API_KEY="sk-or-v1-..."
    # PowerShell : $env:OPENROUTER_API_KEY = "sk-or-v1-..."

La clé vit dans l'environnement, jamais dans le code (Ch. 16) : l'écrire ici
la condamnerait à finir dans l'historique Git.

OpenRouter est une passerelle qui parle le protocole de l'API OpenAI —
`langchain-openai` convient donc tel quel, seules l'adresse du serveur et la
forme de l'identifiant de modèle changent. Une clé unique donne accès aux
modèles de dizaines de fournisseurs, et en changer revient à changer la
constante MODEL ci-dessous.
"""

import os
from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

MODEL = "meta-llama/llama-3-8b-instruct:free"   # sur OpenRouter : fournisseur/modèle
BASE_URL = "https://openrouter.ai/api/v1"

EXPLAIN_PROMPT = ChatPromptTemplate.from_template(
    "Un client a une probabilité de désabonnement de {probability:.0%}. "
    "Ses caractéristiques : contrat {contract}, ancienneté {tenure} mois. "
    "Explique en une phrase, pour un agent de centre d'appel, pourquoi ce "
    "client est à risque et quelle action proposer."
)


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """Client LLM du projet, construit une seule fois.

    Construction paresseuse, pas au niveau du module : importer `explain` ne
    doit pas exiger une clé d'API. Sans ça, `pytest` et le simple
    `from churn_predictor import explain` échouent sur une machine qui n'a
    aucune intention d'appeler un LLM.

    `temperature=0` : la même prédiction doit donner la même explication. Une
    sortie qui change à chaque appel est intestable, et un agent de centre
    d'appel n'a pas à recevoir deux conseils différents pour un même client.

    `os.environ[...]` et non `.get()` : contrairement à `OPENAI_API_KEY`,
    `ChatOpenAI` ne va pas chercher `OPENROUTER_API_KEY` tout seul. Une clé
    absente doit faire échouer l'appel ici, pas partir en requête anonyme
    rejetée en 401 quelques couches plus loin.
    """
    return ChatOpenAI(
        model=MODEL,
        base_url=BASE_URL,
        api_key=os.environ["OPENROUTER_API_KEY"],
        temperature=0,
    )


def explain_prediction(features: dict, probability: float, llm: Runnable | None = None) -> str:
    """Réutilise la prédiction déjà produite par predict.py (Ch. 5).

    `llm` injectable : c'est ce qui rend la fonction testable sans appeler —
    ni payer — une API externe.
    """
    chain = EXPLAIN_PROMPT | (llm or get_llm())
    reponse = chain.invoke({
        "probability": probability,
        "contract": features["Contract"],
        "tenure": features["tenure"],
    })
    return reponse.content
