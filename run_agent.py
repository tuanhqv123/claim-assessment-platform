from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.agent import assess_claim, assess_claim_stream


def run_case(claim_path: str, output_path: str | None = None):
    claim = json.loads(Path(claim_path).read_text())
    print(f"\n{'='*60}")
    print(f"Running: {claim['claim_id']} ({claim['claim_type']})")
    print(f"Amount: {claim['amount']:,.0f} THB")
    print(f"{'='*60}")

    for event in assess_claim_stream(claim):
        if event["type"] == "step":
            print(f"  -> {event['node']}({json.dumps(event['data']['inputs'])})")
        elif event["type"] == "done":
            result = event["final_result"]

    print(f"\nRecommendation: {result['recommendation']}")
    print(f"Reason: {result['recommendation_reason']}")
    print(f"Tool calls: {len(result['tool_call_log'])}")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(result, indent=2, default=str))
        print(f"Output saved to: {output_path}")

    return result


def main():
    cases = [
        ("data/claims/case_1_approve.json", "output/case_1_approve.json"),
        ("data/claims/case_2_reject.json", "output/case_2_reject.json"),
        ("data/claims/case_3_request_info.json", "output/case_3_request_info.json"),
    ]

    if len(sys.argv) > 1:
        claim_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        run_case(claim_path, output_path)
    else:
        for claim_path, output_path in cases:
            run_case(claim_path, output_path)


if __name__ == "__main__":
    main()
