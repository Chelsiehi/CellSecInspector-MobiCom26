#!/usr/bin/env python3
"""Generate one Event 2062 -> 2073 Replay text case from VulnTester_v2 logic."""
import argparse
import json
import os
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"
TARGET = (2062, 2073, "Replay")

SERVICE_INTEGRITY_CONTRACT = {
    "security_property": "Service integrity",
    "attack": "Capture and replay Event 2073 REGISTRATION REQUEST with NG-RAN-RCU toward the AMF.",
    "ordering": "Capture the request, then replay it without requiring the original capability-update registration to complete first.",
    "failure_observation": "The AMF processes the replayed request without sufficient authentication and the existing UE connection or registration context is released, replaced, or disrupted.",
}


def parse_security_md(path: Path) -> list[dict[str, Any]]:
    """Adapted from VulnTester_v2: parse BEGIN_JSON security-analysis rows."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([A-Za-z]+)\s*\|\s*(?:BEGIN_JSON\s*|```json\s*)?(\{.*?\})(?:\s*(?:END_JSON|```))?\s*\|", re.DOTALL | re.MULTILINE)
    rows = []
    for match in pattern.finditer(text):
        try:
            payload = json.loads(match.group(4))
        except json.JSONDecodeError:
            continue
        rows.append({"from": int(match.group(1)), "to": int(match.group(2)), "attack": match.group(3), "json": payload})
    return rows


def parse_connection_blocks(path: Path) -> Dict[Tuple[int, int], Dict[str, Dict[str, str]]]:
    """Adapted from VulnTester_v2: parse source and target SCA fields."""
    text = path.read_text(encoding="utf-8")
    headers = list(re.finditer(r"^===\s*Connection:\s*(\d+)\s*->\s*(\d+)\s*===\s*$", text, re.MULTILINE))
    blocks: Dict[Tuple[int, int], Dict[str, Dict[str, str]]] = {}
    for index, header in enumerate(headers):
        fr, to = int(header.group(1)), int(header.group(2))
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        chunk = text[header.end():end]
        def section(label: str, event_id: int, next_label: str) -> str:
            match = re.search(rf"{label}\s*\({event_id}\):\s*(.*?)(?={next_label}|$)", chunk, re.DOTALL)
            return match.group(1) if match else ""
        def fields(value: str) -> Dict[str, str]:
            return {key: (re.search(rf"{key}:\s*(.*)", value).group(1).strip() if re.search(rf"{key}:\s*(.*)", value) else "") for key in ("Start State", "Condition", "Action", "End State")}
        blocks[(fr, to)] = {"node_i": fields(section("From Event", fr, "To Event")), "node_j": fields(section("To Event", to, "={10}"))}
    return blocks


def build_client() -> OpenAI:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("Missing DEEPSEEK_API_KEY environment variable.")
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def generate_table(client: OpenAI, row: dict[str, Any], details: Dict[str, Dict[str, str]]) -> str:
    """Adapt VulnTester_v2's LLM table prompt for exactly one selected candidate."""
    node_i, node_j, candidate = details["node_i"], details["node_j"], row["json"]
    prompt = "\n".join([
        "You are a mobile network security test engineer specializing in 5G NAS and 5G RRC.",
        "Generate one Markdown table only, with columns: Step, Procedure, U-M, Message, Parameter, Verdict.",
        "U-M contains only →, ←, or –. The Verdict is – until the final row.",
        "",
        "Candidate to validate:", json.dumps(candidate, ensure_ascii=False, indent=2),
        "",
        "Service-integrity semantic contract:", json.dumps(SERVICE_INTEGRITY_CONTRACT, ensure_ascii=False, indent=2),
        "",
        "From Event 2062:", json.dumps(node_i, ensure_ascii=False, indent=2),
        "To Event 2073:", json.dumps(node_j, ensure_ascii=False, indent=2),
        "",
        "Requirements:",
        "- Establish normal registration, then Event 2062 RRC suspension and its RRC-inactive state.",
        "- Describe Event 2073 as capability-update registration triggered by NG-RAN-RCU.",
        "- Capture the Event 2073 REGISTRATION REQUEST, then replay it toward the AMF before requiring the original capability-update registration to complete.",
        "- Do not make NAS counters, nonces, SUCI, MAC checks, duplicate detection, fake RRC connections, or extra responses the primary objective.",
        "- The final verdict is Fail only when the stated existing UE connection or registration-context impact is observed; acceptance or signaling overhead alone is insufficient.",
        "- Output only the Markdown table.",
    ])
    response = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.2, max_tokens=1600)
    return (response.choices[0].message.content or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--security-md", type=Path, default=OUTPUT / "04_security_check.md")
    parser.add_argument("--details-txt", type=Path, default=OUTPUT / "connection_details.txt")
    parser.add_argument("--output", type=Path, default=OUTPUT / "05_text_case.md")
    args = parser.parse_args()
    row = next(item for item in parse_security_md(args.security_md) if (item["from"], item["to"], item["attack"]) == TARGET)
    details = parse_connection_blocks(args.details_txt)[TARGET[:2]]
    table = generate_table(build_client(), row, details)
    args.output.write_text("# Service-Integrity Validation Test Procedure\n\n## Event 2062 -> Event 2073 (Replay)\n\n" + table + "\n", encoding="utf-8")
    print(f"Wrote one text case: {args.output}")


if __name__ == "__main__":
    main()
