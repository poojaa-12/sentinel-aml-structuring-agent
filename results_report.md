# Sentinel AML Structuring Agent - Detailed Results Report

## Run Metadata

- **Dataset:** `data/sample_transactions.csv`
- **Execution mode:** Heuristic fallback (no paid LLM dependency required)
- **Total transactions processed:** `24`
- **Distinct accounts analyzed:** `2`

## Account-Level Outcomes

### Account `ACC_001` (Structuring Scenario)

- **Transaction count:** `10`
- **Total credits:** `$31,300.00`
- **Total debits:** `$31,391.14`
- **Net flow:** `-$91.14`
- **Cash credits:** `3`
- **Wires:** `1`
- **Heuristic risk score:** `100 / 100`
- **Recommendation:** `ESCALATE TO HUMAN`
- **Typology:** `Structuring (Heuristic Detection)`

#### Trigger Evidence (Data Lineage)

- Near-threshold cash deposits:
  - `TXN_1004` -> `$9,500.00`
  - `TXN_1005` -> `$9,800.00`
  - `TXN_1006` -> `$9,900.00`
- Related large outbound wire:
  - `TXN_1007` -> `$29,000.00` to `Binance Offshore`

#### Analyst Interpretation

The account demonstrates a classic structuring sequence: repeated sub-CTR cash deposits clustered across consecutive days, followed by rapid value movement via a high-value wire. This pattern exceeds the heuristic escalation threshold and is surfaced with explicit transaction lineage for auditability.

### Account `ACC_002` (Legitimate Business Cadence Scenario)

- **Transaction count:** `14`
- **Total credits:** `$48,000.00`
- **Total debits:** `$40,700.00`
- **Net flow:** `$7,300.00`
- **Cash credits:** `4`
- **Wires:** `0`
- **Heuristic risk score:** `0 / 100`
- **Recommendation:** `AUTO-RESOLVE`
- **Typology:** `Normal Business Operations`

#### Trigger Evidence (Data Lineage)

- No near-threshold (`$8,000-$9,999`) cash clustering was detected.
- No high-value wire trigger was detected.
- Representative operational lineage IDs in narrative:
  - `TXN_2001`, `TXN_2002`, `TXN_2003`

#### Analyst Interpretation

Despite relatively high cash velocity, this account reflects recurring small-business behavior: regular Monday deposits with routine payroll and vendor outflows. The pattern is cadence-consistent rather than threshold-evasive, so automatic closure is appropriate.

## Validation Against Demo Objectives

1. **Reliable structured output:** Both accounts returned strict AML-style structured results with fixed fields and deterministic recommendation outcomes.
2. **Domain relevance:** The system correctly separated true-positive structuring from false-positive commercial cash activity.
3. **Connector behavior:** Raw CSV ingestion produced clean account-level analysis outputs suitable for API/UI consumption.
4. **Auditability:** Narrative and flagged outputs include transaction IDs supporting compliance traceability.

## Final Summary

Sentinel correctly identified `ACC_001` as a high-risk structuring case and `ACC_002` as normal business activity. The run demonstrates practical AML triage quality, explicit transaction lineage, and cost-aware operation by using a pre-LLM heuristic gate that can run entirely without paid inference.
