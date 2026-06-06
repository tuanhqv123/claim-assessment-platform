import type { ClaimInput } from "@/types/claim";
import type { AssessmentResult } from "@/types/assessment";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface StepEvent {
  type: "step" | "done";
  node?: string;
  data?: Record<string, unknown>;
}

export async function submitAssessmentStream(
  claim: ClaimInput,
  onStep: (event: StepEvent) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(claim),
  });

  if (!res.ok) throw new Error("Assessment failed");
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data: ")) {
        try {
          const event = JSON.parse(trimmed.slice(6)) as StepEvent;
          onStep(event);
        } catch {
          // skip malformed
        }
      }
    }
  }
}

export async function submitAssessmentSync(claim: ClaimInput): Promise<AssessmentResult> {
  const res = await fetch(`${API_BASE}/api/assess/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(claim),
  });
  if (!res.ok) throw new Error("Assessment failed");
  return res.json();
}
