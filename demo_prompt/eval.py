from __future__ import annotations

from pathlib import Path

PROMPT_FRAGMENTS = [
    "- Return valid JSON only.",
    "- Use one label from: billing, technical, refund, other.",
    "- If confidence is below 0.6, use other.",
    "- Do not explain your reasoning.",
    "- Include fields: label, confidence, rationale.",
    "- Confidence must be between 0.0 and 1.0.",
    "- Prefer refund when the user explicitly asks for money back.",
    "- Prefer technical when the user cannot complete a workflow.",
    "- Prefer billing when the issue is about charges or invoices.",
    "- If the ticket mixes categories, pick the user-blocking issue first.",
    "- Never invent labels outside the allowed set.",
    "- Keep rationale under 12 words.",
    "- Example: {\"label\":\"refund\",\"confidence\":0.92,\"rationale\":\"Explicit refund request\"}",
    "- Example: {\"label\":\"technical\",\"confidence\":0.88,\"rationale\":\"Checkout flow blocked\"}",
    "- Reject answers that are not valid JSON.",
    "- When evidence is weak, lower confidence rather than guessing.",
]


def main() -> None:
    text = (Path(__file__).resolve().parent / "prompt.md").read_text(encoding="utf-8")
    score = 84.0 + float(sum(1 for fragment in PROMPT_FRAGMENTS if fragment in text))
    print(f"SCORE={score:.6f}")


if __name__ == "__main__":
    main()
