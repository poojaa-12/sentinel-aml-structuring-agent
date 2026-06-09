# Sentinel: AML Structuring Agent

Sentinel is a constrained, enterprise-style AML demo that ingests raw bank-like CSV data and produces auditable, schema-validated analysis via an LLM.

## Why this demo is different

- **Tamed LLM output:** The model is forced into strict `AMLAnalysisResult` JSON.
- **AML domain signal:** Includes both true-positive structuring and false-positive business cadence scenarios.
- **Connector skills:** Demonstrates realistic ingestion path from messy CSV upload to API analysis and UI rendering.
- **Auditability:** SAR narrative is required to cite transaction IDs for data lineage.

## Project layout

- `backend/app/main.py` - FastAPI app + `/analyze-transactions` endpoint.
- `backend/app/csv_loader.py` - CSV parsing/validation and normalization.
- `backend/app/schemas.py` - Pydantic contracts for transactions and AML output.
- `backend/app/ai_service.py` - Prompting, strict schema response, repair pass.
- `frontend/streamlit_app.py` - Upload UI and severity rendering.
- `data/sample_transactions.csv` - Seeded demo data with required scenarios.
- `backend/tests/` - CSV and schema contract tests.

## Setup

1. Create and activate a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Export API key:

```bash
export OPENAI_API_KEY="your_key_here"
```

Optional model override:

```bash
export OPENAI_MODEL="gpt-4.1-mini"
```

## Run backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## Run Streamlit UI

Open a second terminal:

```bash
streamlit run frontend/streamlit_app.py
```

## Demo script

1. Start backend and Streamlit.
2. In Streamlit, upload `data/sample_transactions.csv`.
3. Confirm output is valid JSON-conformant fields:
   - `account_id`
   - `suspicion_score`
   - `typology_identified`
   - `flagged_transaction_ids`
   - `sar_narrative`
   - `recommendation`
4. Validate true-positive behavior for `ACC_001`:
   - Consecutive sub-$10k cash deposits and follow-up wire to Binance Offshore.
   - Recommendation should trend toward `ESCALATE TO HUMAN`.
5. Validate false-positive behavior for `ACC_002`:
   - Monday $12,000 cash cadence plus payroll/vendor outflows for Joe's Pizza.
   - Recommendation should trend toward `AUTO-RESOLVE`.
6. Confirm SAR narrative cites transaction IDs inline for lineage (e.g., `TXN_1005`).

## Tests

Run tests from repo root:

```bash
PYTHONPATH=backend pytest -q
```
