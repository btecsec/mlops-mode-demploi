"""Corrigé des tests du Chapitre 17.

Aucun appel réseau, aucune clé d'API, aucun jeton facturé : le LLM est injecté
sous forme de `RunnableLambda` qui capture le prompt reçu et renvoie une
réponse choisie par le test. C'est précisément ce que permet le paramètre `llm`
d'`explain_prediction()` et de `judge_explanation()`.

Un test qui appelle un vrai LLM n'est pas un test : il est lent, non
déterministe, et il coûte de l'argent à chaque exécution en CI.

Lancer depuis `chapitre-17/solution/` :  pytest -v
"""

from pathlib import Path

import pytest

pytest.importorskip("langchain_core", reason="voir requirements-llm.txt")

from langchain_core.runnables import RunnableLambda  # noqa: E402

from churn_predictor.explain import EXPLAIN_PROMPT, explain_prediction  # noqa: E402
from churn_predictor.judge import JUDGE_PROMPT, judge_explanation  # noqa: E402

SOLUTION = Path(__file__).resolve().parents[1] / "solution"

FEATURES = {"Contract": "Month-to-month", "tenure": 2}


class FausseReponse:
    """Un message de LLM se réduit, pour ce code, à son attribut `content`."""

    def __init__(self, content: str):
        self.content = content


def faux_llm(reponse: str, capture: list | None = None) -> RunnableLambda:
    """LLM bouchonné : note le prompt reçu, renvoie la réponse demandée."""

    def _appel(prompt_value):
        if capture is not None:
            capture.append(prompt_value.to_string())
        return FausseReponse(reponse)

    return RunnableLambda(_appel)


# --- explain_prediction -------------------------------------------------------

def test_le_prompt_contient_les_donnees_du_client():
    """Un prompt qui oublie une variable produit une explication générique —
    et le LLM ne signale rien : il répond, poliment, à côté."""
    recu: list[str] = []
    explain_prediction(FEATURES, 0.62, llm=faux_llm("peu importe", recu))

    assert "62%" in recu[0]
    assert "Month-to-month" in recu[0]
    assert "2 mois" in recu[0]


def test_la_probabilite_est_formatee_en_pourcentage():
    """`{probability:.0%}` : le LLM reçoit « 62% », pas « 0.6234567 ». Un
    nombre brut se retrouve tel quel dans l'explication lue par l'agent."""
    recu: list[str] = []
    explain_prediction(FEATURES, 0.6234567, llm=faux_llm("x", recu))

    assert "62%" in recu[0]
    assert "0.62" not in recu[0]


def test_la_reponse_du_llm_est_renvoyee_telle_quelle():
    attendu = "Client à risque : contrat mensuel récent, proposer un engagement 12 mois."
    assert explain_prediction(FEATURES, 0.62, llm=faux_llm(attendu)) == attendu


def test_le_prompt_vise_un_agent_de_centre_d_appel():
    """Le destinataire fait la réponse. Sans lui, le LLM produit une analyse
    de data scientist, inutilisable au téléphone."""
    modele = EXPLAIN_PROMPT.messages[0].prompt.template
    assert "agent de centre d'appel" in modele
    assert "une phrase" in modele


# --- judge_explanation --------------------------------------------------------

@pytest.mark.parametrize("brut", ["4", "4/5", "Note : 4", "Je donne 4 sur 5."])
def test_la_note_est_extraite_de_reponses_bavardes(brut):
    """Le cœur du test. `int(raw)` aurait marché en démo et cassé en
    production : un LLM finit toujours par répondre autre chose qu'un chiffre
    nu, malgré la consigne."""
    assert judge_explanation("peu importe", llm=faux_llm(brut)) == 4


def test_une_note_illisible_echoue_explicitement():
    """Mieux vaut une exception nommée qu'un ValueError de `int()` ou, pire,
    une note inventée par défaut."""
    with pytest.raises(ValueError, match="Note illisible"):
        judge_explanation("peu importe", llm=faux_llm("Je ne peux pas noter cela."))


def test_le_juge_recoit_bien_l_explication_a_noter():
    recu: list[str] = []
    judge_explanation("Client à risque, proposer un engagement.", llm=faux_llm("5", recu))
    assert "Client à risque, proposer un engagement." in recu[0]


def test_le_juge_demande_une_echelle_bornee():
    """Sans borne, chaque appel invente son échelle et les notes ne sont plus
    comparables entre elles — donc inexploitables comme métrique."""
    modele = JUDGE_PROMPT.messages[0].prompt.template
    assert "1 à 5" in modele


# --- Les frontières du chapitre -----------------------------------------------

def test_le_llm_n_est_pas_construit_a_l_import():
    """Importer `explain` ne doit pas exiger une clé d'API : sinon `pytest`
    échoue sur une machine qui n'a aucune intention d'appeler un LLM."""
    source = (SOLUTION / "src" / "churn_predictor" / "explain.py").read_text(encoding="utf-8")
    assert "def get_llm" in source
    assert "lru_cache" in source
    # Pas de ChatOpenAI(...) au niveau du module.
    assert not any(
        ligne.startswith("llm = ChatOpenAI") for ligne in source.splitlines()
    )


def test_aucune_cle_d_api_dans_le_code():
    """La clé vient de l'environnement. Écrite ici, elle finirait dans
    l'historique Git — exactement ce que le Chapitre 16 apprend à éviter.

    `api_key=` est cette fois présent dans le code : `ChatOpenAI` ne va pas
    chercher `OPENROUTER_API_KEY` tout seul. Ce qui compte n'est donc plus
    l'absence du mot-clé, mais que sa valeur vienne de `os.environ`."""
    for module in ["explain.py", "judge.py"]:
        source = (SOLUTION / "src" / "churn_predictor" / module).read_text(encoding="utf-8")
        assert "sk-or-v1-changez-moi" not in source
        for ligne in source.splitlines():
            if "api_key=" in ligne:
                assert "os.environ[" in ligne, ligne


def test_le_client_vise_openrouter():
    """Une passerelle plutôt qu'un fournisseur unique : la même clé donne
    accès à des dizaines de modèles, et en changer ne touche qu'une
    constante. Un identifiant sans préfixe de fournisseur part en 404."""
    from churn_predictor.explain import BASE_URL, MODEL

    assert BASE_URL == "https://openrouter.ai/api/v1"
    assert "/" in MODEL


def test_le_llm_est_deterministe():
    """temperature=0 : la même prédiction donne la même explication. Un agent
    de centre d'appel n'a pas à recevoir deux conseils différents pour le même
    client."""
    source = (SOLUTION / "src" / "churn_predictor" / "explain.py").read_text(encoding="utf-8")
    assert "temperature=0" in source


def test_le_llm_ne_remplace_pas_le_modele():
    """Le RandomForest du Chapitre 5 reste seul responsable du chiffre. Le LLM
    traduit un résultat déjà fiable, il ne prédit rien."""
    source = (SOLUTION / "src" / "churn_predictor" / "explain.py").read_text(encoding="utf-8")
    assert "predict_churn" not in source
    assert "probability" in source


def test_les_dependances_llm_sont_isolees():
    principal = (SOLUTION / "requirements.txt").read_text(encoding="utf-8")
    dedie = (SOLUTION / "requirements-llm.txt").read_text(encoding="utf-8")
    assert "langchain" not in principal
    assert "langchain-core" in dedie and "langchain-openai" in dedie
