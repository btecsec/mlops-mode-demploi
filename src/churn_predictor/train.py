from churn_predictor.data import load_raw_data, churn_rate
def main() -> None:
    df = load_raw_data()
    rate = churn_rate(df)
    print(f"Taux de désabonnement (baseline métier) : {rate:.1%}")


if __name__ == "__main__":
    main()
