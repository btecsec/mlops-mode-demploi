from churn_predictor.data import churn_rate, load_raw_data


def main() -> None:
    """Squelette volontairement minimal : le Chapitre 5 remplace ce corps par
    un vrai entraînement scikit-learn sérialisé sur disque."""
    df = load_raw_data()
    rate = churn_rate(df)
    print(f"Taux de désabonnement (baseline métier) : {rate:.1%}")


if __name__ == "__main__":
    main()
