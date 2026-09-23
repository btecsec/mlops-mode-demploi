from typing import Literal

from pydantic import BaseModel, Field

# Les valeurs autorisées viennent directement du CSV : les figer ici fait
# rejeter une faute de frappe par un 422 explicite, au lieu de la laisser
# filer jusqu'au OneHotEncoder qui l'ignorerait silencieusement.
YesNo = Literal["Yes", "No"]
YesNoNoService = Literal["Yes", "No", "No internet service"]


class CustomerFeatures(BaseModel):
    """Les 19 colonnes du dataset Telco Customer Churn (hors customerID et
    Churn), mêmes noms que dans le CSV — la casse compte."""

    gender: Literal["Female", "Male"]
    SeniorCitizen: int = Field(..., ge=0, le=1)
    Partner: YesNo
    Dependents: YesNo
    tenure: int = Field(..., ge=0, description="Ancienneté en mois")
    PhoneService: YesNo
    MultipleLines: Literal["Yes", "No", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: YesNoNoService
    OnlineBackup: YesNoNoService
    DeviceProtection: YesNoNoService
    TechSupport: YesNoNoService
    StreamingTV: YesNoNoService
    StreamingMovies: YesNoNoService
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: YesNo
    PaymentMethod: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ]
    MonthlyCharges: float = Field(..., ge=0)
    TotalCharges: float = Field(..., ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "gender": "Female", "SeniorCitizen": 0, "Partner": "No",
                    "Dependents": "No", "tenure": 2, "PhoneService": "Yes",
                    "MultipleLines": "No", "InternetService": "Fiber optic",
                    "OnlineSecurity": "No", "OnlineBackup": "No",
                    "DeviceProtection": "No", "TechSupport": "No",
                    "StreamingTV": "No", "StreamingMovies": "No",
                    "Contract": "Month-to-month", "PaperlessBilling": "Yes",
                    "PaymentMethod": "Electronic check",
                    "MonthlyCharges": 95.5, "TotalCharges": 191.0,
                }
            ]
        }
    }


class PredictionResponse(BaseModel):
    churn: bool
    probability: float
