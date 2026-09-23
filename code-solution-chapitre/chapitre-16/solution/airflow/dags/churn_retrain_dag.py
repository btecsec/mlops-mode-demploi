"""DAG de ré-entraînement du modèle de churn.

Chapitre 11 : planifié `@weekly`, il réentraîne puis promeut le challenger
seulement s'il bat le champion.

Chapitre 15 : il ne réentraîne plus systématiquement. Une tâche de branchement
mesure d'abord la dérive des données (Couche 2 du monitoring) et n'enclenche
l'entraînement que si le seuil est franchi. Le calendrier dit *quand regarder* ;
le drift dit *s'il y a lieu d'agir*.

Installation : garder AIRFLOW_HOME côté Linux (SQLite verrouille mal sur
/mnt/c) et pointer le dossier de DAGs sur celui du projet.

    export AIRFLOW_HOME=~/airflow
    export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/airflow/dags
    airflow standalone

Airflow ne tourne pas nativement sous Windows : l'installation passe, mais le
lancement s'arrête sur `AttributeError: module 'os' has no attribute
'register_at_fork'`. Passer par WSL2 ou l'image Docker officielle.
"""

from datetime import datetime, timedelta

from airflow.decorators import dag, task


@dag(
    schedule="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,          # ne rattrape pas les exécutions passées manquées
    tags=["churn-predictor"],
)
def churn_retrain_pipeline():

    @task.branch
    def should_retrain() -> str:
        """Ne déclenche le ré-entraînement que si le drift dépasse le seuil.

        Import local : le scheduler parse ce fichier toutes les quelques
        secondes pour découvrir les DAG. Charger Evidently à chaque passage
        rendrait ce parsing lent, et une erreur d'import ferait disparaître le
        DAG entier de l'interface.
        """
        from monitoring.check_drift import DRIFT_THRESHOLD, check_drift

        return "train_challenger" if check_drift() > DRIFT_THRESHOLD else "skip_retrain"

    # retries + retry_delay : le piège du Chapitre 11. Un ré-entraînement qui
    # échoue en silence chaque semaine laisse le champion vieillir sans que
    # personne ne le soupçonne.
    @task(retries=2, retry_delay=timedelta(minutes=5))
    def train_challenger() -> dict:
        """Entraîne un nouveau run MLflow, retourne son identifiant et son accuracy."""
        from churn_predictor.train import train_and_save

        run_id, accuracy = train_and_save()
        # Un XCom doit être sérialisable en JSON : un str et un float passent,
        # un objet scikit-learn non.
        return {"run_id": run_id, "accuracy": accuracy}

    @task(retries=2, retry_delay=timedelta(minutes=5))
    def evaluate_and_promote(challenger: dict) -> str:
        """Compare au champion actuel, promeut seulement si meilleur."""
        from churn_predictor.evaluate import get_champion_accuracy, promote_challenger

        current_accuracy = get_champion_accuracy()
        challenger_accuracy = challenger["accuracy"]
        if challenger_accuracy > current_accuracy:
            # On promeut le run qu'on vient de mesurer, désigné par son
            # identifiant — pas « le dernier arrivé dans le Registry ».
            version = promote_challenger(challenger["run_id"])
            return f"promu (v{version}) : {challenger_accuracy:.3f} > {current_accuracy:.3f}"
        return f"conservé : challenger {challenger_accuracy:.3f} <= actuel {current_accuracy:.3f}"

    @task
    def skip_retrain() -> str:
        """Branche « rien à faire ». Une tâche explicite plutôt qu'un chemin
        mort : dans l'interface, on voit que le DAG a tourné et *décidé*, au
        lieu de se demander s'il a planté."""
        return "drift sous le seuil : champion conservé, aucun ré-entraînement"

    decision = should_retrain()
    decision >> evaluate_and_promote(train_challenger())
    decision >> skip_retrain()


churn_retrain_pipeline()
