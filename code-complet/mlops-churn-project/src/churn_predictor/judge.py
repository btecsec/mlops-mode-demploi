import re

from langchain_core.prompts import ChatPromptTemplate

# même client que explain.py : une seule configuration de LLM dans le projet
from churn_predictor.explain import get_llm

JUDGE_PROMPT = ChatPromptTemplate.from_template(
    "Explication donnée à un agent : \"{explanation}\"\n"
    "Note de 1 à 5 sa clarté et son utilité opérationnelle. "
    "Réponds uniquement par un chiffre."
)


def judge_explanation(explanation: str) -> int:
    """Un second LLM note la sortie du premier - même logique de
    validation indépendante que le champion/challenger du Ch. 11,
    appliquée ici à du texte plutôt qu'à une accuracy."""
    chain = JUDGE_PROMPT | get_llm()
    raw = chain.invoke({"explanation": explanation}).content

    note = re.search(r"[1-5]", raw)   # tolère "4", "4/5", "Note : 4"
    if note is None:
        raise ValueError(f"Note illisible renvoyée par le juge : {raw!r}")
    return int(note.group())