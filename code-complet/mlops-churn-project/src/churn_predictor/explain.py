import os
from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

MODEL = "nvidia/nemotron-3.5-lightning:free"   # sur OpenRouter : fournisseur/modèle
BASE_URL = "https://openrouter.ai/api/v1"

EXPLAIN_PROMPT = ChatPromptTemplate.from_template(
    "Un client a une probabilité de désabonnement de {probability:.0%}. "
    "Ses caractéristiques : contrat {contract}, ancienneté {tenure} mois. "
    "Explique en une phrase, pour un agent de centre d'appel, pourquoi ce "
    "client est à risque et quelle action proposer."
)


@lru_cache(maxsize=1)   # construit une fois, et seulement si on s'en sert
def get_llm() -> ChatOpenAI:
    """Construction paresseuse : importer ce module ne doit pas exiger de clé.

    Au niveau du module, un simple `import explain` échouerait sur une machine
    qui n'a aucune intention d'appeler un LLM — pytest le premier.
    """
    return ChatOpenAI(
        model=MODEL,
        base_url=BASE_URL,
        api_key=os.environ["OPENROUTER_API_KEY"],   # absente : le programme s'arrête ici
        temperature=0,                              # limite la variabilité d'un appel à l'autre
    )


def explain_prediction(features: dict, probability: float) -> str:
    """Réutilise la prédiction déjà produite par predict.py (Ch. 5) :
    le LLM n'entraîne rien, il traduit un chiffre en explication utile."""
    chain = EXPLAIN_PROMPT | get_llm()
    response = chain.invoke({
        "probability": probability,
        "contract": features["Contract"],
        "tenure": features["tenure"],
    })
    return response.content
