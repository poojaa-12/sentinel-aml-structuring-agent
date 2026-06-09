from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import ValidationError

from .ai_service import LLMOutputValidationError, analyze_transactions
from .csv_loader import CSVValidationError, parse_transactions_from_csv
from .schemas import AMLAnalysisResult

app = FastAPI(title="Sentinel AML Structuring Agent", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-transactions", response_model=AMLAnalysisResult)
async def analyze_transactions_endpoint(file: UploadFile = File(...)) -> AMLAnalysisResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="CSV must be UTF-8 encoded text."
        ) from exc

    try:
        transactions = parse_transactions_from_csv(text)
    except CSVValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid transaction values: {exc.errors()}"
        ) from exc

    try:
        result = analyze_transactions(transactions)
    except LLMOutputValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail="Model response failed schema validation. Please retry.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result
