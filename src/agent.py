from __future__ import annotations

import json
import os
from typing import Generator

from dotenv import load_dotenv
from openai import OpenAI

from src.config import require_env
from src.stores.policy_store import PolicyStore
from src.stores.document_store import DocumentStore
from src.stores.medical_mapping import MedicalMapping
from src.nodes.calculate_benefit import BenefitCalculator

load_dotenv()

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "lookupPolicy",
            "description": "Look up insurance policy terms by policy ID. Returns benefits, limits, exclusions, copay, waiting periods, member list, and coverage dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "policyId": {"type": "string", "description": "The policy ID (e.g. POL-001)"},
                },
                "required": ["policyId"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verifyDocument",
            "description": "Verify a submitted document's type, completeness status, and any issues found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "documentId": {"type": "string", "description": "The document ID (e.g. DOC-001)"},
                },
                "required": ["documentId"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkMedicalNecessity",
            "description": "Check whether the treatment procedures are clinically appropriate for the diagnosis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "diagnosis": {"type": "string", "description": "ICD-10 diagnosis code"},
                    "procedures": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of procedure/CPT codes",
                    },
                },
                "required": ["diagnosis", "procedures"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculateBenefit",
            "description": "Calculate the covered amount, copay, and remaining limit for a claim against the policy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "policyId": {"type": "string"},
                    "claimType": {"type": "string", "description": "OUTPATIENT, INPATIENT, DENTAL, or MATERNITY"},
                    "subBenefit": {"type": "string", "description": "Sub-benefit name (e.g. Doctor Visit, Surgery)"},
                    "amount": {"type": "number"},
                    "claimDate": {"type": "string", "description": "Claim date in YYYY-MM-DD format"},
                    "diagnosisDescription": {"type": "string"},
                },
                "required": ["policyId", "claimType", "subBenefit", "amount", "claimDate", "diagnosisDescription"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "retrievePolicyClauses",
            "description": (
                "Semantically search the full policy document for the clauses most "
                "relevant to a question (e.g. 'is cosmetic surgery excluded?', "
                "'what counts as medically necessary?', 'waiting period for this "
                "condition'). Use this for qualitative/wording questions that the "
                "structured lookupPolicy result cannot answer. Returns the matching "
                "clause text with its section heading, which you must quote in "
                "policy_citations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "policyId": {"type": "string", "description": "The policy ID (e.g. POL-001)"},
                    "query": {
                        "type": "string",
                        "description": "A natural-language question about the policy wording",
                    },
                },
                "required": ["policyId", "query"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are an insurance claim assessor. You receive a claim and must assess it step by step using the tools available to you.

PROCESS — follow this sequence:
1. Call lookupPolicy to get the policy terms. Check: is the policy active? Is the member covered? Is the claim date within the coverage period?
2. Call verifyDocument for EVERY document in the submitted documents list. Do not skip any. Check which required documents are present vs missing.
3. If any required document is missing, recommend REQUEST_MORE_INFO (do NOT reject for missing documents). Specify which documents are missing.
4. If all documents are present, call checkMedicalNecessity to verify the treatment is appropriate for the diagnosis.
5. Call retrievePolicyClauses to check the policy wording for anything that could change the decision: is the diagnosis/procedure EXCLUDED? does it meet the policy's definition of "medically necessary"? is a waiting period relevant? Search with a focused question and read the returned clauses. If a clause excludes the treatment, recommend REJECT and cite that clause.
6. If medically necessary and not excluded, call calculateBenefit to determine the covered amount.
7. Based on all the above, produce your assessment report.

REQUIRED DOCUMENTS by claim type:
- OUTPATIENT: medical_receipt (required)
- INPATIENT: medical_receipt, discharge_summary, itemized_bill (all required)
- DENTAL: dental_receipt (required)

REPORT FORMAT — your final response must be a JSON object with these 6 sections:
{
  "document_review": [{"document_id": "...", "type": "...", "status": "...", "issues": "..."}],
  "policy_verification": {"policy_active": bool, "member_covered": bool, "claim_type_covered": bool, "coverage_period_valid": bool, "details": "..."},
  "medical_necessity": {"is_appropriate": bool or null, "reasoning": "...", "warnings": []},
  "benefit_calculation": {"submitted_amount": "...", "covered_amount": "...", "copay_amount": "...", "member_pays": "...", "remaining_limit": "...", "breakdown": "..."},
  "recommendation": {"decision": "APPROVE|REJECT|REQUEST_MORE_INFO", "reasoning": "...", "next_steps": "..."},
  "policy_citations": [{"clause": "...", "relevance": "..."}]
}

RULES:
- NEVER state policy terms from memory. Always call lookupPolicy first.
- Every recommendation must cite specific policy clauses — from the structured lookupPolicy result (for numbers/limits) and/or the retrievePolicyClauses result (for exclusions, definitions and conditions). Quote the clause text you relied on.
- Use retrievePolicyClauses (not memory) to decide exclusions and medical-necessity wording questions.
- If a field is not available (e.g. benefit calculation when documents are missing), use "Not available".
- Missing document → REQUEST_MORE_INFO. Never REJECT for missing documents.
- Format amounts with currency (e.g. "2,500 THB").
- Your final message must be ONLY the JSON report, no other text.
"""


_policy_store = PolicyStore()
_doc_store = DocumentStore()
_medical_mapping = MedicalMapping()


def _execute_tool(
    name: str,
    args: dict,
    doc_store: DocumentStore | None = None,
    policy_store: PolicyStore | None = None,
) -> str:
    pstore = policy_store or _policy_store
    if name == "lookupPolicy":
        result = pstore.lookup(args["policyId"])
        if result is None:
            return json.dumps({"error": f"Policy {args['policyId']} not found"})
        return json.dumps(result, default=str)

    if name == "verifyDocument":
        store = doc_store or _doc_store
        result = store.verify(args["documentId"])
        return json.dumps(result)

    if name == "checkMedicalNecessity":
        result = _medical_mapping.check(args["diagnosis"], args["procedures"])
        return json.dumps(result)

    if name == "retrievePolicyClauses":
        from src.rag import service

        policy = pstore.lookup(args["policyId"])
        if policy is None:
            return json.dumps({"error": f"Policy {args['policyId']} not found"})
        # Make sure this policy's document is indexed (resolves uploaded text or
        # renders one from the structured terms), then search it.
        service.ensure_indexed(args["policyId"], policy)
        clauses = service.retrieve(args["policyId"], args["query"], k=4)
        return json.dumps({"query": args["query"], "clauses": clauses})

    if name == "calculateBenefit":
        calculator = BenefitCalculator()
        policy = pstore.lookup(args["policyId"])
        if policy is None:
            return json.dumps({"error": "Policy not found"})
        result = calculator.calculate(
            policy=policy,
            claim_type=args["claimType"],
            sub_benefit_name=args["subBenefit"],
            amount=args["amount"],
            claim_date=args["claimDate"],
            diagnosis_description=args.get("diagnosisDescription", ""),
        )
        return json.dumps(result, default=str)

    return json.dumps({"error": f"Unknown tool: {name}"})


def _get_client() -> tuple[OpenAI, str]:
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    model = require_env("OPENAI_MODEL")
    return client, model


def assess_claim(
    claim: dict,
    doc_store: DocumentStore | None = None,
    policy_store: PolicyStore | None = None,
) -> dict:
    """Run the full assessment. Returns {recommendation, report, tool_call_log}.

    ``doc_store`` / ``policy_store`` optionally override the stores so
    verifyDocument and lookupPolicy/retrievePolicyClauses resolve real DB-backed
    data instead of the file-backed demo stores.
    """
    steps = list(
        assess_claim_stream(claim, doc_store=doc_store, policy_store=policy_store)
    )
    last = steps[-1]
    return last.get("final_result", {})


def assess_claim_stream(
    claim: dict,
    doc_store: DocumentStore | None = None,
    policy_store: PolicyStore | None = None,
) -> Generator[dict, None, None]:
    """Stream assessment steps. Yields {type, node, data} per tool call, then {type: done, final_result}."""
    client, model = _get_client()

    claim_summary = (
        f"Assess this insurance claim:\n"
        f"- Claim ID: {claim['claim_id']}\n"
        f"- Policy ID: {claim['policy_id']}\n"
        f"- Member ID: {claim['member_id']}\n"
        f"- Claim Type: {claim['claim_type']}\n"
        f"- Sub-benefit: {claim['sub_benefit']}\n"
        f"- Diagnosis: {claim['diagnosis_code']} — {claim['diagnosis_description']}\n"
        f"- Procedure Codes: {', '.join(claim['procedure_codes'])}\n"
        f"- Amount: {claim['amount']:,.0f} THB\n"
        f"- Claim Date: {claim['claim_date']}\n"
        f"- Provider: {claim['provider']}\n"
        f"- Submitted Documents: {', '.join(claim['submitted_document_ids'])}\n"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": claim_summary},
    ]

    tool_call_log = []
    max_iterations = 15

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            temperature=0,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or (choice.message.tool_calls and len(choice.message.tool_calls) > 0):
            messages.append(choice.message)

            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)

                tool_result = _execute_tool(fn_name, fn_args, doc_store, policy_store)

                log_entry = {
                    "tool_name": fn_name,
                    "inputs": fn_args,
                    "outputs": json.loads(tool_result) if tool_result.startswith("{") or tool_result.startswith("[") else tool_result,
                }
                tool_call_log.append(log_entry)

                yield {"type": "step", "node": fn_name, "data": log_entry}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })
        else:
            report_text = choice.message.content or ""
            report = _parse_report(report_text)

            recommendation = "UNKNOWN"
            recommendation_reason = ""
            if report and "recommendation" in report:
                recommendation = report["recommendation"].get("decision", "UNKNOWN")
                recommendation_reason = report["recommendation"].get("reasoning", "")

            final = {
                "claim_id": claim["claim_id"],
                "recommendation": recommendation,
                "recommendation_reason": recommendation_reason,
                "report": report,
                "tool_call_log": tool_call_log,
            }

            yield {"type": "done", "final_result": final}
            return

    yield {"type": "done", "final_result": {
        "claim_id": claim["claim_id"],
        "recommendation": "ERROR",
        "recommendation_reason": "Max iterations reached",
        "report": None,
        "tool_call_log": tool_call_log,
    }}


def _parse_report(text: str) -> dict | None:
    import re
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Extract JSON object from anywhere in the text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"raw_text": text, "parse_error": True}
