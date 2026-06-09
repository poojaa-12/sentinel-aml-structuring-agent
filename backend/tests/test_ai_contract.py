from __future__ import annotations

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.ai_service import _heuristic_risk_score, analyze_transactions
from app.schemas import AMLAnalysisResult, TransactionDirection, TransactionRecord


def test_aml_analysis_result_contract_accepts_expected_shape() -> None:
    payload = {
        "account_id": "ACC_001",
        "suspicion_score": 95,
        "typology_identified": "Structuring",
        "flagged_transaction_ids": ["TXN_1004", "TXN_1005", "TXN_1006", "TXN_1007"],
        "sar_narrative": (
            "Paragraph 1 cites TXN_1004 and TXN_1005.\n\n"
            "Paragraph 2 cites TXN_1006 and TXN_1007.\n\n"
            "Paragraph 3 recommends escalation with cited lineage."
        ),
        "recommendation": "ESCALATE TO HUMAN",
    }
    result = AMLAnalysisResult.model_validate(payload)
    assert result.suspicion_score == 95
    assert "TXN_1007" in result.flagged_transaction_ids


def test_aml_analysis_result_rejects_invalid_recommendation() -> None:
    payload = {
        "account_id": "ACC_002",
        "suspicion_score": 10,
        "typology_identified": "Normal Business Operations",
        "flagged_transaction_ids": ["TXN_2001"],
        "sar_narrative": "Narrative with TXN_2001.",
        "recommendation": "IGNORE",
    }
    with pytest.raises(ValidationError):
        AMLAnalysisResult.model_validate(payload)


def test_transaction_record_serialization_for_prompting() -> None:
    record = TransactionRecord(
        transaction_id="TXN_9999",
        account_id="ACC_999",
        timestamp=datetime.fromisoformat("2026-04-10T13:30:00"),
        amount=9500.00,
        currency="USD",
        direction=TransactionDirection.CREDIT,
        channel="cash",
        counterparty_name="Branch 17",
        transaction_type="cash_deposit",
        memo="test",
    )
    dumped = json.loads(record.model_dump_json())
    assert dumped["direction"] == "credit"


def test_heuristic_risk_score_detects_structuring_pattern() -> None:
    transactions = [
        TransactionRecord(
            transaction_id="TXN_1004",
            account_id="ACC_001",
            timestamp=datetime.fromisoformat("2026-04-10T13:30:00"),
            amount=9500.00,
            currency="USD",
            direction=TransactionDirection.CREDIT,
            channel="cash",
            counterparty_name="Branch 17",
            transaction_type="cash_deposit",
            memo="in branch deposit",
        ),
        TransactionRecord(
            transaction_id="TXN_1005",
            account_id="ACC_001",
            timestamp=datetime.fromisoformat("2026-04-11T10:05:00"),
            amount=9800.00,
            currency="USD",
            direction=TransactionDirection.CREDIT,
            channel="cash",
            counterparty_name="Branch 17",
            transaction_type="cash_deposit",
            memo="in branch deposit",
        ),
        TransactionRecord(
            transaction_id="TXN_1007",
            account_id="ACC_001",
            timestamp=datetime.fromisoformat("2026-04-14T16:40:00"),
            amount=29000.00,
            currency="USD",
            direction=TransactionDirection.DEBIT,
            channel="wire",
            counterparty_name="Binance Offshore",
            transaction_type="wire_transfer",
            memo="international wire",
        ),
    ]

    risk_score, flagged_ids, _ = _heuristic_risk_score(transactions)
    assert risk_score >= 40
    assert "TXN_1004" in flagged_ids
    assert "TXN_1007" in flagged_ids


def test_analyze_transactions_short_circuits_low_risk_without_api_key() -> None:
    transactions = [
        TransactionRecord(
            transaction_id="TXN_2001",
            account_id="ACC_002",
            timestamp=datetime.fromisoformat("2026-04-06T08:30:00"),
            amount=12000.00,
            currency="USD",
            direction=TransactionDirection.CREDIT,
            channel="cash",
            counterparty_name="Downtown Branch",
            transaction_type="cash_deposit",
            memo="monday register drop Joe's Pizza",
        ),
        TransactionRecord(
            transaction_id="TXN_2002",
            account_id="ACC_002",
            timestamp=datetime.fromisoformat("2026-04-06T15:15:00"),
            amount=4200.00,
            currency="USD",
            direction=TransactionDirection.DEBIT,
            channel="ach",
            counterparty_name="Fresh Farm Produce",
            transaction_type="vendor_payment",
            memo="ingredients supplier",
        ),
    ]
    result = analyze_transactions(transactions)
    assert result.recommendation == "AUTO-RESOLVE"
    assert result.suspicion_score < 40
