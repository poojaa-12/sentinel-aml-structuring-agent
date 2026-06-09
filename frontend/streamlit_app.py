from __future__ import annotations

import json
from io import BytesIO

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/analyze-transactions"


def _banner_html(color: str, text: str) -> str:
    return (
        f"<div style='padding:0.75rem;border-radius:0.5rem;background-color:{color};"
        "font-weight:700;color:white;'>"
        f"{text}</div>"
    )


st.set_page_config(page_title="Sentinel AML Structuring Agent", layout="wide")
st.title("Sentinel: AML Structuring Agent")
st.caption("Schema-constrained AML analysis with auditable transaction lineage.")

uploaded_file = st.file_uploader("Upload transaction CSV", type=["csv"])

if uploaded_file:
    st.subheader("Ready to analyze")
    st.write(
        "This will call the FastAPI backend and return a strict AMLAnalysisResult payload."
    )
    if st.button("Run Analysis", type="primary"):
        with st.spinner("Analyzing transactions..."):
            files = {
                "file": (uploaded_file.name, BytesIO(uploaded_file.getvalue()), "text/csv")
            }
            try:
                response = requests.post(API_URL, files=files, timeout=90)
            except requests.RequestException as exc:
                st.error(f"API request failed: {exc}")
            else:
                if response.status_code != 200:
                    try:
                        detail = response.json().get("detail", "Unknown API error.")
                    except json.JSONDecodeError:
                        detail = response.text
                    st.error(f"Analysis failed ({response.status_code}): {detail}")
                else:
                    result = response.json()
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
else:
    st.info("Upload `data/sample_transactions.csv` to run the full demo scenario.")
