from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PurchaseStructuredFields(BaseModel):
    """Поля из FR-IN-02. Все необязательные."""

    address: str | None = None
    work_type: str | None = None
    desired_dates: str | None = None
    constraints: str | None = None
    contractor_requirements: str | None = None
    budget: str | None = None


class PurchaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10_000)
    structured_fields: PurchaseStructuredFields = Field(
        default_factory=PurchaseStructuredFields
    )


class PurchaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    structured_fields: dict
    status: str
    purchase_type: str | None
    analysis: dict | None
    created_at: datetime
    updated_at: datetime
