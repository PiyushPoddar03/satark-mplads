"""Pydantic schemas for Expense Bills & Material Invoices."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class BillItemInput(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=50)
    claimed_unit_price: float = Field(..., ge=0)
    total_amount: float | None = None


class BillCreateRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    vendor_name: str = Field(..., min_length=2, max_length=255)
    invoice_number: str | None = Field(None, max_length=100)
    bill_date: datetime = Field(default_factory=lambda: datetime.now())
    items: list[BillItemInput] = Field(..., min_length=1)
    file_url: str | None = None
    file_name: str | None = None


class EvaluatedBillItemResponse(BaseModel):
    item_name: str
    category: str
    quantity: float
    unit: str
    claimed_unit_price: float
    total_amount: float
    benchmark_unit_price: float
    deviation_pct: float
    status: str
    notes: str


class ExpenseBillResponse(BaseModel):
    id: str
    bill_code: str
    project_id: str
    project_code: str | None = None
    project_name: str | None = None
    inspector_user_id: str
    inspector_name: str | None = None
    vendor_name: str
    invoice_number: str | None = None
    bill_date: str
    total_amount: float
    file_url: str | None = None
    file_name: str | None = None
    items: list[dict]
    overall_deviation_pct: float
    anomaly_score: float
    fraud_risk_level: str
    ai_analysis_summary: str | None = None
    status: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MaterialBenchmarkResponse(BaseModel):
    category: str
    name: str
    unit: str
    benchmark_price: float
    tolerance_pct: float
    description: str
