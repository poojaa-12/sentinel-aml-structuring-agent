from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, conint


class TransactionDirection(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionRecord(BaseModel):
    transaction_id: str = Field(description="Unique transaction identifier.")
    account_id: str = Field(description="Bank account identifier.")
    timestamp: datetime = Field(description="Transaction timestamp in ISO format.")
    amount: float = Field(gt=0, description="Transaction amount in account currency.")
    currency: str = Field(description="ISO currency code, e.g. USD.")
    direction: TransactionDirection = Field(description="credit or debit.")
    channel: str = Field(description="Transaction channel, e.g. cash, wire, card.")
    counterparty_name: str = Field(description="Counterparty or branch name.")
    transaction_type: str = Field(description="Internal transaction type classification.")
    memo: str = Field(default="", description="Free-form transaction memo.")


class AMLAnalysisResult(BaseModel):
    account_id: str
    suspicion_score: conint(ge=0, le=100) = Field(
        description="Score from 0 to 100 indicating likelihood of money laundering."
    )
    typology_identified: str = Field(
        description="Typology label such as Structuring, Smurfing, or Normal Business Operations."
    )
    flagged_transaction_ids: list[str] = Field(
        description="Exact transaction IDs that drove the decision."
    )
    sar_narrative: str = Field(
        description="Three-paragraph SAR narrative suitable for regulator review with transaction citations."
    )
    recommendation: Literal["AUTO-RESOLVE", "ESCALATE TO HUMAN"]
