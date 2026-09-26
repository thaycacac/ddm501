"""
Pydantic schemas for request/response validation.

The schema is the API's contract. Everything the model assumes about its input
is stated here, so a malformed request fails at the edge with a clear 422
instead of producing a confident-looking wrong score.
"""

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class CreditApplication(BaseModel):
    """One applicant, as the core banking system sends it."""

    limit_bal: float = Field(
        ..., gt=0, le=2_000_000, description="Credit limit in NT dollars", examples=[120000]
    )
    sex: Literal[1, 2] = Field(..., description="1 = male, 2 = female", examples=[2])
    education: Literal[1, 2, 3, 4] = Field(
        ..., description="1 = graduate school, 2 = university, 3 = high school, 4 = others",
        examples=[2],
    )
    marriage: Literal[1, 2, 3] = Field(
        ..., description="1 = married, 2 = single, 3 = others", examples=[2]
    )
    age: int = Field(..., ge=18, le=100, description="Age in years", examples=[34])
    pay_status: List[int] = Field(
        ...,
        min_length=6,
        max_length=6,
        description=(
            "Repayment status for months t-1 .. t-6. "
            "-2 = no consumption, -1 = paid in full, 0 = revolving credit, "
            "1..8 = months of payment delay."
        ),
        examples=[[0, 0, 0, 0, 0, 0]],
    )
    bill_amt: List[float] = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Bill statement amounts for months t-1 .. t-6",
        examples=[[12000, 11500, 11000, 10500, 10000, 9500]],
    )
    pay_amt: List[float] = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Amounts paid for months t-1 .. t-6",
        examples=[[12000, 11500, 11000, 10500, 10000, 9500]],
    )

    @field_validator("pay_status")
    @classmethod
    def pay_status_in_domain(cls, values: List[int]) -> List[int]:
        for value in values:
            if value < -2 or value > 8:
                raise ValueError("each pay_status value must be between -2 and 8 inclusive")
        return values

    @field_validator("pay_amt")
    @classmethod
    def pay_amt_non_negative(cls, values: List[float]) -> List[float]:
        for value in values:
            if value < 0:
                raise ValueError("pay_amt values must not be negative")
        return values


class PredictionResponse(BaseModel):
    """Scoring result plus the decision derived from it."""

    default_probability: float = Field(..., ge=0.0, le=1.0)
    risk_band: Literal["LOW", "MEDIUM", "HIGH"]
    decision: Literal["APPROVE", "REVIEW", "DECLINE"]
    review_threshold: float
    decline_threshold: float
    model_version: str


class HealthResponse(BaseModel):
    """Liveness and readiness of the service."""

    status: Literal["healthy", "unhealthy"]
    model_loaded: bool
    model_version: str


class BatchPredictionRequest(BaseModel):
    """Up to 500 applications scored in one call."""

    applications: List[CreditApplication] = Field(..., min_length=1, max_length=500)


class BatchPredictionResponse(BaseModel):
    """Results in the same order as the request."""

    predictions: List[PredictionResponse]
    total_count: int
