from __future__ import annotations

from pathlib import Path

import pytest

from app.csv_loader import CSVValidationError, parse_transactions_from_csv


def test_parse_sample_transactions_file() -> None:
    root = Path(__file__).resolve().parents[2]
    sample_path = root / "data" / "sample_transactions.csv"
    records = parse_transactions_from_csv(sample_path.read_text())
    assert len(records) >= 20
    assert any(r.transaction_id == "TXN_1007" for r in records)
    assert any(r.transaction_id == "TXN_2001" for r in records)


def test_parse_transactions_missing_columns_raises() -> None:
    bad_csv = "transaction_id,account_id\nTXN_1,ACC_1\n"
    with pytest.raises(CSVValidationError):
        parse_transactions_from_csv(bad_csv)
