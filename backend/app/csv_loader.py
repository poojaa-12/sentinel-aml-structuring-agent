from __future__ import annotations

from io import StringIO

import pandas as pd

from .schemas import TransactionDirection, TransactionRecord

REQUIRED_COLUMNS = {
    "transaction_id",
    "account_id",
    "timestamp",
    "amount",
    "currency",
    "direction",
    "channel",
    "counterparty_name",
    "transaction_type",
    "memo",
}


class CSVValidationError(ValueError):
    pass


def parse_transactions_from_csv(csv_text: str) -> list[TransactionRecord]:
    if not csv_text.strip():
        raise CSVValidationError("CSV payload is empty.")

    frame = pd.read_csv(StringIO(csv_text))
    if frame.empty:
        raise CSVValidationError("CSV file has no transaction rows.")

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise CSVValidationError(f"Missing required CSV columns: {missing_text}")

    frame = frame.loc[:, sorted(REQUIRED_COLUMNS)]
    frame["direction"] = frame["direction"].astype(str).str.lower().str.strip()

    invalid_directions = set(frame["direction"].unique()).difference(
        {d.value for d in TransactionDirection}
    )
    if invalid_directions:
        bad_values = ", ".join(sorted(invalid_directions))
        raise CSVValidationError(f"Invalid direction values: {bad_values}")

    records: list[TransactionRecord] = []
    for row in frame.to_dict(orient="records"):
        records.append(TransactionRecord.model_validate(row))

    return records
