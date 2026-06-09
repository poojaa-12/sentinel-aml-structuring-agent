from __future__ import annotations

import json
from collections import Counter

from openai import AuthenticationError, OpenAI, OpenAIError
from pydantic import ValidationError

from .config import settings
from .schemas import AMLAnalysisResult, TransactionRecord


class LLMOutputValidationError(RuntimeError):
    pass


SYSTEM_PROMPT = """
You are a senior AML compliance officer specializing in structuring detection.
You must produce only JSON that exactly matches the provided schema.
Use formal, regulator-ready language.
When writing sar_narrative, include exact transaction IDs inline to preserve data lineage.
""".strip()


def _primary_account_id(transactions: list[TransactionRecord]) -> str:
    if not transactions:
        return "UNKNOWN_ACCOUNT"
    counts = Counter(t.account_id for t in transactions)
    return counts.most_common(1)[0][0]


def _heuristic_risk_score(
    transactions: list[TransactionRecord],
) -> tuple[int, list[str], list[TransactionRecord]]:
    cash_near_threshold = [
        t
        for t in transactions
        if t.direction.value == "credit" and t.channel.lower() == "cash" and 8000 <= t.amount < 10000
    ]
    cash_near_threshold.sort(key=lambda t: t.timestamp)

    large_wires = [
        t
        for t in transactions
        if t.direction.value == "debit" and t.channel.lower() == "wire" and t.amount >= 25000
    ]

    score = min(len(cash_near_threshold) * 20, 60)
    flagged = [t.transaction_id for t in cash_near_threshold]

    if len(cash_near_threshold) >= 2:
        for idx in range(len(cash_near_threshold) - 1):
            delta_days = (
                cash_near_threshold[idx + 1].timestamp - cash_near_threshold[idx].timestamp
            ).days
            if delta_days <= 2:
                score += 20
                break

    if len(cash_near_threshold) >= 3:
        score += 10

    if large_wires:
        score += 20
        flagged.extend(t.transaction_id for t in large_wires)

    score = min(score, 100)
    flagged = list(dict.fromkeys(flagged))
    return score, flagged, cash_near_threshold


def _auto_resolve_from_heuristic(
    transactions: list[TransactionRecord], risk_score: int
) -> AMLAnalysisResult:
    account_id = _primary_account_id(transactions)
    sample_ids = [t.transaction_id for t in sorted(transactions, key=lambda x: x.timestamp)[:3]]
    lineage_text = ", ".join(sample_ids) if sample_ids else "No transaction IDs available."
    narrative = (
        "Automated heuristic pre-check found no strong structuring indicators at this time. "
        f"Observed transactions include {lineage_text}, and no suspicious cluster of sub-$10,000 "
        "cash deposits was detected.\n\n"
        "Cash flow appears operationally consistent without abrupt sequencing patterns that suggest "
        "reporting-threshold evasion. Transaction cadence is more aligned to routine account activity "
        "than deliberate layering or smurfing behavior.\n\n"
        "Given low heuristic risk and absence of high-risk trigger combinations, this case is "
        "recommended for automated closure with ongoing monitoring retained."
    )
    return AMLAnalysisResult(
        account_id=account_id,
        suspicion_score=risk_score,
        typology_identified="Normal Business Operations",
        flagged_transaction_ids=sample_ids,
        sar_narrative=narrative,
        recommendation="AUTO-RESOLVE",
    )


def _build_user_prompt(transactions: list[TransactionRecord]) -> str:
    serialized = [
        {
            "transaction_id": t.transaction_id,
            "account_id": t.account_id,
            "timestamp": t.timestamp.isoformat(),
            "amount": t.amount,
            "currency": t.currency,
            "direction": t.direction.value,
            "channel": t.channel,
            "counterparty_name": t.counterparty_name,
            "transaction_type": t.transaction_type,
            "memo": t.memo,
        }
        for t in transactions
    ]
    return (
        "Review this transaction log for potential structuring or normal business patterns. "
        "If activity reflects legitimate business cadence, choose AUTO-RESOLVE. "
        "If suspicious structuring or laundering indicators exist, choose ESCALATE TO HUMAN. "
        "Output JSON only and follow the schema exactly.\n\n"
        f"Transactions:\n{json.dumps(serialized, indent=2)}"
    )


def _extract_json_text(response) -> str:
    try:
        return response.output_text
    except AttributeError:
        # Fallback for SDK responses that expose content in older shapes.
        return str(response)


def _request_analysis(
    client: OpenAI, prompt: str, validation_hint: str | None = None
) -> AMLAnalysisResult:
    user_input = prompt
    if validation_hint:
        user_input = (
            f"{prompt}\n\nPrevious output failed validation:\n{validation_hint}\n"
            "Repair the JSON and return valid JSON only."
        )

    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "aml_analysis_result",
                "schema": AMLAnalysisResult.model_json_schema(),
                "strict": True,
            }
        },
    )

    payload = _extract_json_text(response)
    return AMLAnalysisResult.model_validate_json(payload)


def analyze_transactions(transactions: list[TransactionRecord]) -> AMLAnalysisResult:
    risk_score, flagged_ids, _ = _heuristic_risk_score(transactions)
    if risk_score < 40:
        return _auto_resolve_from_heuristic(transactions=transactions, risk_score=risk_score)

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to run analysis.")

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = _build_user_prompt(transactions)
    try:
        try:
            return _request_analysis(client=client, prompt=prompt)
        except ValidationError as exc:
            try:
                return _request_analysis(
                    client=client, prompt=prompt, validation_hint=exc.json()
                )
            except ValidationError as final_exc:
                raise LLMOutputValidationError(
                    "Model output failed schema validation after repair attempt."
                ) from final_exc
    except AuthenticationError as exc:
        raise RuntimeError(
            "OpenAI authentication failed. Check OPENAI_API_KEY in Streamlit Secrets."
        ) from exc
    except OpenAIError as exc:
        raise RuntimeError(
            "OpenAI request failed. Verify model access, billing, and API key configuration."
        ) from exc
