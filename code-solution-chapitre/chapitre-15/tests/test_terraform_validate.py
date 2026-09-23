"""Corrigé des tests du Chapitre 13.

Deux niveaux, pour deux raisons :

1. `terraform fmt -check` — le vrai outil, quand il est installé. Il ne
   contacte aucun cloud et ne coûte rien. `terraform validate`, lui, exige un
   `terraform init` préalable qui télécharge le provider Google (plusieurs
   centaines de Mo) : hors de portée d'une suite de tests, et impossible sur
   un poste hors ligne. Le README explique comment le lancer à la main.
2. Des assertions de structure sur le HCL lui-même — toujours exécutables,
   même sans Terraform installé. Ce qu'elles verrouillent, ce sont les
   décisions qui coûtent cher : un state local, un identifiant de projet en
   dur, un provider non épinglé.

Lancer depuis `chapitre-13/solution/` :  pytest -v
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SOLUTION = Path(__file__).resolve().parents[1] / "solution"
INFRA = SOLUTION / "infra"


def lire(nom: str) -> str:
    return (INFRA / nom).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def hcl() -> str:
    """Tous les .tf concaténés : les blocs peuvent vivre dans n'importe quel
    fichier, Terraform les lit comme un seul ensemble."""
    return "\n".join(f.read_text(encoding="utf-8") for f in sorted(INFRA.glob("*.tf")))


# --- Structure attendue -------------------------------------------------------

@pytest.mark.parametrize(
    "fichier", ["backend.tf", "providers.tf", "variables.tf", "main.tf", "outputs.tf"]
)
def test_chaque_fichier_attendu_existe(fichier):
    assert (INFRA / fichier).is_file()


def test_terraform_fmt(hcl):
    """Le formatage canonique, vérifié par Terraform lui-même quand il est
    disponible. Aucun appel réseau, aucun provider téléchargé."""
    if shutil.which("terraform") is None:
        pytest.skip("terraform absent du PATH")
    resultat = subprocess.run(
        ["terraform", "fmt", "-check", "-recursive", str(INFRA)],
        capture_output=True,
        text=True,
    )
    assert resultat.returncode == 0, f"à reformater :\n{resultat.stdout}"


# --- Le piège du chapitre : le state ------------------------------------------

def test_le_state_est_distant():
    """Un state local, c'est deux personnes qui s'écrasent mutuellement sans
    le savoir — et une infrastructure entière oubliée le jour où la machine
    change."""
    backend = lire("backend.tf")
    assert re.search(r'backend\s+"(gcs|s3|azurerm|remote)"', backend)


def test_le_state_n_est_jamais_commite():
    gitignore = (SOLUTION / ".gitignore").read_text(encoding="utf-8")
    for motif in ["*.tfstate", "*.tfvars", "infra/.terraform/"]:
        assert motif in gitignore, f"{motif} manque au .gitignore"
    # L'exemple, lui, doit rester versionné : c'est de la documentation.
    assert "!*.tfvars.example" in gitignore


def test_aucun_tfstate_ni_tfvars_dans_le_depot():
    """Ceinture et bretelles : le .gitignore peut être correct et un fichier
    avoir été forcé avec `git add -f` avant qu'il n'existe."""
    interdits = list(INFRA.glob("*.tfstate*")) + [
        f for f in INFRA.glob("*.tfvars") if not f.name.endswith(".example")
    ]
    assert interdits == [], f"fichiers à ne jamais versionner : {interdits}"


# --- Rien en dur --------------------------------------------------------------

def test_le_project_id_n_a_pas_de_valeur_par_defaut():
    """Un identifiant de projet cloud en dur dans un fichier partagé, c'est le
    TP d'un lecteur qui déploie chez un autre."""
    bloc = re.search(
        r'variable\s+"project_id"\s*\{(.*?)\n\}', lire("variables.tf"), re.DOTALL
    )
    assert bloc, "variable project_id absente"
    assert "default" not in bloc.group(1)


def test_le_cluster_est_parametre(hcl):
    """Un `resource` qui code en dur son nom, sa région et sa taille n'est pas
    réutilisable d'un environnement à l'autre."""
    bloc = re.search(
        r'resource\s+"google_container_cluster".*?\n\}', hcl, re.DOTALL
    ).group(0)
    for champ in ["var.cluster_name", "var.region", "var.node_count"]:
        assert champ in bloc, f"{champ} n'est pas utilisé dans la ressource"


def test_le_cluster_est_destructible(hcl):
    """`deletion_protection` vaut `true` par defaut depuis le provider Google 6.
    Laisse tel quel, `terraform destroy` refuse de partir — et un cluster GKE
    oublie facture chaque heure qui passe."""
    bloc = re.search(
        r'resource\s+"google_container_cluster".*?\n\}', hcl, re.DOTALL
    ).group(0)
    assert re.search(r"deletion_protection\s*=\s*false", bloc), (
        "sans deletion_protection = false, le terraform destroy de fin de TP echoue"
    )


def test_le_pare_feu_ouvre_le_nodeport(hcl):
    """Un Service NodePort ouvre le port cote Kubernetes, pas cote reseau. Sans
    regle de pare-feu, la connexion part et n'obtient jamais de reponse : un
    timeout, pas un `connection refused`. La regle vise l'etiquette posee sur
    les noeuds, pas tout le reseau."""
    bloc = re.search(
        r'resource\s+"google_compute_firewall".*?\n\}\n', hcl, re.DOTALL
    )
    assert bloc, "aucune regle de pare-feu : le NodePort restera injoignable"
    regle = bloc.group(0)
    assert "var.node_port" in regle, "le port ouvert doit venir de var.node_port"
    assert "var.node_tag" in regle, "sans target_tags, la regle vise tout le reseau"
    assert "var.allowed_source_ranges" in regle


def test_le_nodeport_du_chart_et_du_pare_feu_sont_alignes():
    """L'incoherence que ni Terraform ni Helm ne peuvent voir : le pare-feu
    autorise un port, le chart en ouvre un autre. Les deux fichiers sont
    valides separement, et l'API ne repond pas."""
    defaut = re.search(
        r'variable\s+"node_port"\s*\{(.*?)\n\}', lire("variables.tf"), re.DOTALL
    )
    assert defaut, "variable node_port absente"
    port_terraform = re.search(r"default\s*=\s*(\d+)", defaut.group(1)).group(1)

    values = (SOLUTION / "churn-api-chart" / "values.yaml").read_text(encoding="utf-8")
    port_helm = re.search(r"^\s+nodePort:\s*(\d+)", values, re.M)
    assert port_helm, "service.nodePort absent de values.yaml"
    assert port_helm.group(1) == port_terraform, (
        f"pare-feu sur {port_terraform}, chart sur {port_helm.group(1)}"
    )


def test_le_provider_est_epingle(hcl):
    """Sans contrainte de version, un `terraform init` lancé six mois plus tard
    récupère une version majeure aux ressources renommées : le plan diverge
    sans qu'une ligne de code ait bougé."""
    assert "required_version" in hcl
    bloc = re.search(r"required_providers\s*\{.*?\n  \}", hcl, re.DOTALL)
    assert bloc and re.search(r'version\s*=\s*"[~>=<]', bloc.group(0))


# --- Sorties ------------------------------------------------------------------

def test_l_endpoint_du_cluster_est_expose_et_marque_sensible():
    """L'endpoint sert à `gcloud container clusters get-credentials`. Sans
    `sensitive = true`, il s'affiche en clair dans les logs d'un apply en CI."""
    outputs = lire("outputs.tf")
    assert "cluster_endpoint" in outputs
    bloc = re.search(r'output\s+"cluster_endpoint"\s*\{(.*?)\n\}', outputs, re.DOTALL)
    assert "sensitive" in bloc.group(1)


def test_un_exemple_de_tfvars_est_fourni():
    """Sans valeur pour project_id, Terraform s'interrompt sur
    `var.project_id: Enter a value:` — blocage garanti en CI."""
    exemple = (INFRA / "terraform.tfvars.example").read_text(encoding="utf-8")
    assert "project_id" in exemple
