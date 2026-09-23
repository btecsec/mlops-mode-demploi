"""LLM-as-a-judge : un second LLM note la sortie du premier.

Même principe qu'au Chapitre 11 — ne jamais promouvoir un résultat sans mesure
indépendante — appliqué à du texte plutôt qu'à une accuracy. Le juge ne
remplace pas une relecture humaine, il la rend tenable à l'échelle : on relit
les notes basses, pas les mille explications.
"""

import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

# Même client que explain.py : une seule configuration de LLM dans le projet.
from churn_predictor.explain import get_llm

JUDGE_PROMPT = ChatPromptTemplate.from_template(
    'Explication donnée à un agent : "{explanation}"\n'
    "Note de 1 à 5 sa clarté et son utilité opérationnelle. "
    "Réponds uniquement par un chiffre."
)

NOTE_MINIMALE = 3   # en dessous, l'explication repart en relecture humaine


def judge_explanation(explanation: str, llm: Runnable | None = None) -> int:
    """Note une explication de 1 à 5.

    `int(raw)` aurait été la version naïve. Un LLM finit toujours par répondre
    « 4/5 » ou « Note : 4 » malgré la consigne, et le pipeline casse en
    production sur une réponse parfaitement raisonnable. On extrait le chiffre,
    et on échoue explicitement quand il n'y en a pas — même réflexe que la
    validation Pydantic du Chapitre 5, appliquée à une sortie de LLM.
    """
    chain = JUDGE_PROMPT | (llm or get_llm())
    brut = chain.invoke({"explanation": explanation}).content

    note = re.search(r"[1-5]", brut)
    if note is None:
        raise ValueError(f"Note illisible renvoyée par le juge : {brut!r}")
    return int(note.group())
