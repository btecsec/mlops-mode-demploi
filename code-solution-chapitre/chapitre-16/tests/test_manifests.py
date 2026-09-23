"""Corrigé des tests du Chapitre 12.

Un manifeste Kubernetes accepté par `kubectl apply` n'est pas pour autant un
manifeste correct : les oublis du chapitre (`resources.requests`,
`readinessProbe`) ne produisent aucune erreur — juste un HPA inerte et des
requêtes servies trop tôt. C'est exactement ce que ces tests verrouillent.

Aucun cluster n'est nécessaire : tout est vérifiable en lisant du YAML.

Lancer depuis `chapitre-12/solution/` :  pytest -v
"""

from pathlib import Path

import pytest
import yaml

SOLUTION = Path(__file__).resolve().parents[1] / "solution"
K8S = SOLUTION / "k8s"
CHART = SOLUTION / "churn-api-chart"


def charger(nom: str) -> dict:
    return yaml.safe_load((K8S / nom).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def deployment() -> dict:
    return charger("deployment.yaml")


@pytest.fixture(scope="module")
def container(deployment) -> dict:
    return deployment["spec"]["template"]["spec"]["containers"][0]


# --- Les quatre manifestes ----------------------------------------------------

@pytest.mark.parametrize(
    ("fichier", "kind"),
    [
        ("configmap.yaml", "ConfigMap"),
        ("deployment.yaml", "Deployment"),
        ("service.yaml", "Service"),
        ("hpa.yaml", "HorizontalPodAutoscaler"),
    ],
)
def test_chaque_manifeste_declare_le_bon_kind(fichier, kind):
    assert charger(fichier)["kind"] == kind


def test_plusieurs_replicas_demandes(deployment):
    """Un seul replica, c'est le `docker run` du Chapitre 6 avec plus d'étapes :
    toujours un point de défaillance unique."""
    assert deployment["spec"]["replicas"] >= 2


def test_le_service_pointe_sur_le_port_du_container(deployment, container):
    """Le bug silencieux classique : le Service expose bien un port, mais pas
    celui qu'uvicorn écoute. Les Pods sont Running, le curl expire."""
    port_container = container["ports"][0]["containerPort"]
    assert charger("service.yaml")["spec"]["ports"][0]["targetPort"] == port_container


def test_le_service_selectionne_les_pods_du_deployment(deployment):
    """Un label qui ne correspond pas, et le Service ne route vers rien —
    sans la moindre erreur affichée."""
    assert charger("service.yaml")["spec"]["selector"] == deployment["spec"]["selector"]["matchLabels"]


# --- Le piège du chapitre -----------------------------------------------------

def test_resources_requests_declarees(container):
    """Sans `requests`, le HPA n'a aucune base pour calculer un pourcentage de
    charge : il reste inerte, silencieusement."""
    requests = container["resources"]["requests"]
    assert "cpu" in requests and "memory" in requests


@pytest.mark.parametrize("probe", ["readinessProbe", "livenessProbe"])
def test_les_probes_interrogent_health(container, probe):
    """Sans readinessProbe, Kubernetes route du trafic vers un Pod qui démarre
    mais n'a pas fini de charger le modèle : `Running` ne veut pas dire
    « répond correctement »."""
    assert container[probe]["httpGet"]["path"] == "/health"


# --- Le HPA -------------------------------------------------------------------

def test_le_hpa_cible_le_bon_deployment(deployment):
    hpa = charger("hpa.yaml")
    assert hpa["spec"]["scaleTargetRef"]["name"] == deployment["metadata"]["name"]
    assert hpa["spec"]["minReplicas"] < hpa["spec"]["maxReplicas"]


# --- Configuration externalisée -----------------------------------------------

def test_la_configmap_est_injectee_dans_le_container(container):
    sources = [list(s)[0] for s in container["envFrom"]]
    assert "configMapRef" in sources
    assert "secretRef" in sources


def test_l_alias_du_modele_n_est_pas_un_stage():
    """Les stages MLflow ("Production", "Staging") sont l'ancienne API,
    abandonnée dès le Chapitre 7 au profit des alias."""
    assert charger("configmap.yaml")["data"]["MODEL_ALIAS"] == "champion"


def test_la_config_est_lue_par_l_application():
    """Une ConfigMap que le code ignore est décorative. `config.py` doit lire
    la variable d'environnement, avec la valeur locale en repli."""
    config = (SOLUTION / "src" / "churn_predictor" / "config.py").read_text(encoding="utf-8")
    assert 'os.getenv(\n    "MLFLOW_TRACKING_URI"' in config
    assert 'os.getenv("MODEL_ALIAS"' in config


def test_aucun_secret_en_clair_dans_les_manifestes():
    """Le Secret se crée avec `kubectl create secret`, hors du dépôt. Aucun
    fichier de k8s/ ne doit contenir de valeur sensible."""
    for fichier in K8S.glob("*.yaml"):
        # safe_load_all : mlflow.yaml porte trois documents séparés par `---`.
        for doc in yaml.safe_load_all(fichier.read_text(encoding="utf-8")):
            assert doc["kind"] != "Secret", fichier.name


# --- Le chart Helm ------------------------------------------------------------

def test_le_chart_declare_ses_deux_versions():
    """`version` est celle du chart, `appVersion` celle de l'application. Les
    confondre est la première source de confusion sur un chart partagé."""
    chart = yaml.safe_load((CHART / "Chart.yaml").read_text(encoding="utf-8"))
    assert chart["apiVersion"] == "v2"
    assert "version" in chart and "appVersion" in chart


def test_les_valeurs_variables_sont_dans_values_yaml():
    """Ce qui change d'un environnement à l'autre appartient à values.yaml,
    pas aux templates."""
    values = yaml.safe_load((CHART / "values.yaml").read_text(encoding="utf-8"))
    assert values["image"]["repository"].startswith("ghcr.io/")
    assert values["autoscaling"]["minReplicas"] < values["autoscaling"]["maxReplicas"]
    assert values["resources"]["requests"]["cpu"]


@pytest.mark.parametrize(
    "template", ["configmap.yaml", "deployment.yaml", "service.yaml", "hpa.yaml"]
)
def test_les_templates_ne_contiennent_aucune_valeur_en_dur(template):
    """Un template qui code en dur l'image ou le nombre de replicas ne sert à
    rien : autant appliquer les manifestes de k8s/ directement."""
    contenu = (CHART / "templates" / template).read_text(encoding="utf-8")
    assert "{{" in contenu, f"{template} n'utilise aucune valeur paramétrable"
    assert "ghcr.io/" not in contenu


def test_le_deployment_du_chart_ne_fige_pas_les_replicas_sous_hpa():
    """Fixer `replicas` alors que le HPA est actif annule le travail de
    l'autoscaler à chaque `helm upgrade` : le compteur repart à sa valeur
    d'origine, puis remonte, en boucle."""
    contenu = (CHART / "templates" / "deployment.yaml").read_text(encoding="utf-8")
    assert "if not .Values.autoscaling.enabled" in contenu


# --- Durcissement du Deployment (Chapitre 16) --------------------------------


def _pod_spec():
    d = yaml.safe_load((K8S / "deployment.yaml").read_text(encoding="utf-8"))
    return d["spec"]["template"]["spec"]


def test_pod_tourne_sans_privilege():
    """`runAsNonRoot` seul ne suffit pas : sans `runAsUser`, Kubernetes fait
    confiance à l'image. Et sans `fsGroup`, le volume des logs reste root:root
    et l'application ne peut pas y écrire — panne silencieuse au premier
    /predict du Chapitre 15."""
    sc = _pod_spec()["securityContext"]
    assert sc["runAsNonRoot"] is True
    assert sc["runAsUser"] == 10001
    assert sc["fsGroup"] == 10001


def test_container_verrouille():
    sc = _pod_spec()["containers"][0]["securityContext"]
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["readOnlyRootFilesystem"] is True
    assert sc["capabilities"]["drop"] == ["ALL"]


def test_les_seuls_chemins_inscriptibles_sont_montes():
    """readOnlyRootFilesystem casse toute écriture non prévue : les deux
    chemins dont l'application a besoin doivent être des volumes."""
    spec = _pod_spec()
    montes = {m["mountPath"] for m in spec["containers"][0]["volumeMounts"]}
    assert {"/app/logs", "/tmp"} <= montes
    assert {v["name"] for v in spec["volumes"]} >= {"logs", "tmp"}


def test_uid_coherent_entre_dockerfile_et_manifeste():
    """Un uid qui diverge entre l'image et le manifeste, et le volume des logs
    appartient à quelqu'un d'autre que le processus."""
    dockerfile = (SOLUTION / "Dockerfile").read_text(encoding="utf-8")
    assert "--uid 10001" in dockerfile
    assert _pod_spec()["securityContext"]["runAsUser"] == 10001
