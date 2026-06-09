from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from app.ai_service import LLMOutputValidationError, analyze_transactions
from app.csv_loader import CSVValidationError, parse_transactions_from_csv
from pydantic import ValidationError

API_URL = os.getenv("BACKEND_API_URL", "").strip()
SAMPLE_CSV_PATH = REPO_ROOT / "data" / "sample_transactions.csv"


def _banner_html(color: str, text: str) -> str:
    return (
        f"<div style='padding:0.75rem;border-radius:0.5rem;background-color:{color};"
        "font-weight:700;color:white;'>"
        f"{text}</div>"
    )


def _render_result(result: dict) -> None:
    st.subheader("AML Analysis Result")
    col1, col2, col3 = st.columns(3)
    col1.metric("Account ID", result["account_id"])
    col2.metric("Suspicion Score", result["suspicion_score"])
    col3.metric("Typology", result["typology_identified"])
    st.write("**Flagged Transaction IDs**")
    st.code(", ".join(result["flagged_transaction_ids"]))

    recommendation = result["recommendation"]
    if recommendation == "ESCALATE TO HUMAN":
        st.markdown(
            _banner_html("#cc0000", "Recommendation: ESCALATE TO HUMAN"),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            _banner_html("#1e8e3e", "Recommendation: AUTO-RESOLVE"),
            unsafe_allow_html=True,
        )

    with st.expander("SAR Narrative", expanded=True):
        st.write(result["sar_narrative"])


def _run_analysis(csv_name: str, csv_bytes: bytes) -> None:
    with st.spinner("Analyzing transactions..."):
        if API_URL:
            files = {"file": (csv_name, csv_bytes, "text/csv")}
            try:
                response = requests.post(API_URL, files=files, timeout=90)
            except requests.RequestException as exc:
                st.error(f"API request failed: {exc}")
            else:
                if response.status_code != 200:
                    try:
                        detail = response.json().get("detail", "Unknown API error.")
                    except ValueError:
                        detail = response.text
                    st.error(f"Analysis failed ({response.status_code}): {detail}")
                else:
                    _render_result(response.json())
        else:
            try:
                csv_text = csv_bytes.decode("utf-8")
                transactions = parse_transactions_from_csv(csv_text)
                result = analyze_transactions(transactions)
                _render_result(result.model_dump())
            except UnicodeDecodeError:
                st.error("CSV must be UTF-8 encoded text.")
            except CSVValidationError as exc:
                st.error(f"CSV validation failed: {exc}")
            except ValidationError as exc:
                st.error(f"Transaction validation failed: {exc}")
            except LLMOutputValidationError:
                st.error("Model response failed schema validation. Please retry.")
            except RuntimeError as exc:
                st.error(str(exc))


st.set_page_config(page_title="Sentinel AML Structuring Agent", layout="wide")
st.title("Sentinel: AML Structuring Agent")
st.caption("Schema-constrained AML analysis with auditable transaction lineage.")

if API_URL:
    st.info(f"Mode: API (`{API_URL}`)")
else:
    st.info("Mode: Direct analysis (Cloud-ready, no separate FastAPI deploy required).")

if SAMPLE_CSV_PATH.exists():
    sample_csv_bytes = SAMPLE_CSV_PATH.read_bytes()
    col_download, col_demo = st.columns(2)
    with col_download:
        st.download_button(
            "Download Sample CSV",
            data=sample_csv_bytes,
            file_name="sample_transactions.csv",
            mime="text/csv",
        )
    with col_demo:
        if st.button("Run Demo with Sample Data"):
            _run_analysis("sample_transactions.csv", sample_csv_bytes)
else:
    st.warning("Sample data file not found at `data/sample_transactions.csv`.")

st.divider()

uploaded_file = st.file_uploader("Upload transaction CSV", type=["csv"])

if uploaded_file:
    st.subheader("Ready to analyze")
    if API_URL:
        st.write(
            "This will call the configured FastAPI backend and return a strict AMLAnalysisResult payload."
        )
    else:
        st.write(
            "This runs CSV parsing + heuristic gate + LLM analysis directly inside Streamlit."
        )
    if st.button("Run Analysis", type="primary"):
        _run_analysis(uploaded_file.name, uploaded_file.getvalue())
else:
    st.info("Upload `data/sample_transactions.csv` to run the full demo scenario.")
