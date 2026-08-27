from churn_predictor.data import load_raw_data, churn_rate


def test_dataset_shape():
    df = load_raw_data()
    assert df.shape == (7043, 21)


def test_churn_rate_is_realistic():
    df = load_raw_data()
    rate = churn_rate(df)
    assert 0.20 < rate < 0.30  # baseline connue depuis le chapitre 0
