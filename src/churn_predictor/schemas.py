from pydantic import BaseModel, Field


class CustomerFeatures(BaseModel):
    """Les 19 colonnes du dataset Telco Customer Churn (hors customerID et
    Churn), mêmes noms que dans le CSV. train.py entraîne le pipeline sur
    ces 19 colonnes : il en faut 19 aussi à la prédiction, sinon le
    ColumnTransformer lève 'columns are missing'."""

    gender: str
    SeniorCitizen: int = Field(..., ge=0, le=1)
    Partner: str
    Dependents: str
    tenure: int = Field(..., ge=0, description="Ancienneté en mois")
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str = Field(..., examples=["Month-to-month", "One year", "Two year"])
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: float = Field(..., ge=0)
    TotalCharges: float = Field(..., ge=0)


class PredictionResponse(BaseModel):
    churn: bool
    probability: float
