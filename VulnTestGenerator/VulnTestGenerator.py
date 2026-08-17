"""Generate concrete vulnerability test procedures from security-analysis outputs.

This script links two artifacts:
- a Markdown file that contains per-connection security analysis results
- a connection-detail text file that contains the source/target event context

For each selected connection, it asks a DeepSeek model to generate a concrete test
procedure as a Markdown table.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from openai import OpenAI

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 4096
DEFAULT_SECURITY_MD = "data/security_analysis_results_5g.md"
DEFAULT_DETAILS_TXT = "data/connection_details_output_5g.txt"
DEFAULT_OUTPUT_MD = "outputs/all_testcases_step_procedures.md"
ATTACK_TYPES = ("Inject", "Drop", "Modify", "Replay")
DETAILS_SEPARATOR = "========================================"
FIELD_NAMES = ("Start State", "Condition", "Action", "End State")
ROW_START_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([A-Za-z]+)\s*\|")
CONNECTION_HEADER_RE = re.compile(
    r"^===\s*Connection:\s*(\d+)\s*->\s*(\d+)\s*===\s*$",
    re.MULTILINE,
)


@dataclass
class SecurityRow:
    """One security-analysis entry parsed from a Markdown table."""

    from_id: int
    to_id: int
    attack: str
    payload: dict[str, Any]


@dataclass
class EventContext:
    """Structured event fields extracted from the connection-detail file."""

    start_state: str
    condition: str
    action: str
    end_state: str


@dataclass
class ConnectionContext:
    """Context for one directed connection between two events."""

    from_id: int
    to_id: int
    node_i: EventContext
    node_j: EventContext



def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Generate vulnerability test procedures from security-analysis results."
    )
    parser.add_argument(
        "--security-md",
        default=DEFAULT_SECURITY_MD,
        help=f"Path to the security analysis Markdown file. Defaults to {DEFAULT_SECURITY_MD}.",
    )
    parser.add_argument(
        "--details-txt",
        default=DEFAULT_DETAILS_TXT,
        help=f"Path to the connection-details text file. Defaults to {DEFAULT_DETAILS_TXT}.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_MD,
        help=f"Path to the generated Markdown report. Defaults to {DEFAULT_OUTPUT_MD}.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("DEEPSEEK_API_KEY"),
        help="DeepSeek API key. Defaults to the DEEPSEEK_API_KEY environment variable.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        help=f"DeepSeek API base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
        help=f"Model name. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"Sampling temperature. Defaults to {DEFAULT_TEMPERATURE}.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Maximum completion tokens. Defaults to {DEFAULT_MAX_TOKENS}.",
    )
    parser.add_argument(
        "--include-non-vulnerable",
        action="store_true",
        help="Generate procedures for all rows, not only rows with vulnerability_detected = Yes.",
    )
    return parser.parse_args()



def validate_args(args: argparse.Namespace) -> None:
    """Validate file paths and required runtime configuration."""
    if not os.path.isfile(args.security_md):
        raise FileNotFoundError(f"Security analysis file not found: {args.security_md}")
    if not os.path.isfile(args.details_txt):
        raise FileNotFoundError(f"Connection details file not found: {args.details_txt}")
    if not args.api_key:
        raise ValueError(
            "Missing DeepSeek API key. Set DEEPSEEK_API_KEY or pass --api-key."
        )

    output_dir = os.path.dirname(os.path.abspath(args.output)) or "."
    os.makedirs(output_dir, exist_ok=True)



def load_json_payload(blob: str) -> Optional[dict[str, Any]]:
    """Parse a JSON-like payload with a best-effort json5 fallback."""
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        try:
            import json5  # type: ignore
        except Exception:
            return None
        try:
            return json5.loads(blob)
        except Exception:
            return None



def extract_json_blob(text: str) -> Optional[str]:
    """Extract the structured analysis payload from a Markdown table cell."""
    begin_end_match = re.search(
        r"BEGIN_JSON\s*(\{.*?\})\s*END_JSON",
        text,
        re.DOTALL,
    )
    if begin_end_match:
        return begin_end_match.group(1).strip()

    fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        return fenced_match.group(1).strip()

    raw_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if raw_match:
        return raw_match.group(1).strip()

    return None



def parse_security_md(path: str) -> list[SecurityRow]:
    """Parse security-analysis rows from a Markdown table with multiline cells."""
    with open(path, "r", encoding="utf-8") as input_file:
        lines = input_file.readlines()

    rows: list[SecurityRow] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        row_match = ROW_START_RE.match(line)
        if not row_match:
            index += 1
            continue

        from_id = int(row_match.group(1))
        to_id = int(row_match.group(2))
        attack = row_match.group(3).strip()
        block_lines = [line]
        index += 1

        while index < len(lines) and not ROW_START_RE.match(lines[index]):
            block_lines.append(lines[index])
            index += 1

        block_text = "".join(block_lines)
        json_blob = extract_json_blob(block_text)
        if json_blob is None:
            print(f"[WARN] Skip row without JSON payload: {from_id}->{to_id} {attack}")
            continue

        payload = load_json_payload(json_blob)
        if payload is None:
            print(f"[WARN] Skip invalid JSON payload: {from_id}->{to_id} {attack}")
            continue

        rows.append(
            SecurityRow(
                from_id=from_id,
                to_id=to_id,
                attack=attack,
                payload=payload,
            )
        )

    return rows



def extract_field(text: str, field_name: str) -> str:
    """Extract one event field from a raw event subsection."""
    match = re.search(rf"{re.escape(field_name)}:\s*(.*)", text)
    return match.group(1).strip() if match else ""



def parse_event_context(text: str) -> EventContext:
    """Convert a raw event subsection into a structured event context."""
    return EventContext(
        start_state=extract_field(text, "Start State"),
        condition=extract_field(text, "Condition"),
        action=extract_field(text, "Action"),
        end_state=extract_field(text, "End State"),
    )



def parse_connection_contexts(path: str) -> dict[tuple[int, int], ConnectionContext]:
    """Parse all connection blocks from the connection-details text file."""
    with open(path, "r", encoding="utf-8") as input_file:
        text = input_file.read()

    matches = list(CONNECTION_HEADER_RE.finditer(text))
    contexts: dict[tuple[int, int], ConnectionContext] = {}

    for idx, match in enumerate(matches):
        from_id = int(match.group(1))
        to_id = int(match.group(2))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        chunk = text[start:end]

        from_section_match = re.search(
            rf"From Event\s*\({from_id}\):\s*(.*?)\s*To Event\s*\({to_id}\):",
            chunk,
            re.DOTALL,
        )
        to_section_match = re.search(
            rf"To Event\s*\({to_id}\):\s*(.*?)(?:{re.escape(DETAILS_SEPARATOR)}|$)",
            chunk,
            re.DOTALL,
        )

        if not from_section_match or not to_section_match:
            print(f"[WARN] Skip unparsable connection context: {from_id}->{to_id}")
            continue

        contexts[(from_id, to_id)] = ConnectionContext(
            from_id=from_id,
            to_id=to_id,
            node_i=parse_event_context(from_section_match.group(1)),
            node_j=parse_event_context(to_section_match.group(1)),
        )

    return contexts



def is_vulnerability_detected(payload: dict[str, Any]) -> bool:
    """Return True when the security-analysis row reports a real vulnerability."""
    verdict = str(payload.get("vulnerability_detected", "")).strip().lower()
    return verdict == "yes"



def build_client(api_key: str, base_url: str) -> OpenAI:
    """Create an OpenAI-compatible client configured for DeepSeek."""
    return OpenAI(api_key=api_key, base_url=base_url)



def generate_prompt(
    attack: str,
    context: ConnectionContext,
    payload: dict[str, Any],
) -> str:
    """Build the LLM prompt used to synthesize a concrete test procedure."""
    context_json = json.dumps(payload, indent=2, ensure_ascii=False)
    return f"""You are a mobile network security test engineer specializing in 5G NAS, LTE NAS, and 5G RRC.

Design a concrete vulnerability validation procedure and output ONLY a Markdown table in the following format:

| Step | Procedure | U-M | Message | Parameter | Verdict |
|---:|---|:---:|---|---|---|

Requirements:
- Provide 5 to 10 concrete steps.
- Keep each step operational and test-oriented.
- Use realistic telecom signaling terminology.
- The Verdict column should describe the expected observable result for that step.
- Do not add any prose before or after the table.

Attack type: {attack}

node_i:
- Start State: {context.node_i.start_state}
- Condition: {context.node_i.condition}
- Action: {context.node_i.action}
- End State: {context.node_i.end_state}

node_j:
- Start State: {context.node_j.start_state}
- Condition: {context.node_j.condition}
- Action: {context.node_j.action}
- End State: {context.node_j.end_state}

Security analysis context:
```json
{context_json}
```
"""



def request_test_table(
    client: OpenAI,
    model_name: str,
    temperature: float,
    max_tokens: int,
    attack: str,
    context: ConnectionContext,
    payload: dict[str, Any],
) -> str:
    """Call the model and return the generated Markdown table."""
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a cellular security test expert."},
            {
                "role": "user",
                "content": generate_prompt(attack=attack, context=context, payload=payload),
            },
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()



def normalize_table_output(text: str) -> str:
    """Extract the Markdown table from the model response when possible."""
    table_match = re.search(
        r"(\|\s*Step\s*\|.*?)(?=\n\s*[^|]|$)",
        text,
        re.DOTALL,
    )
    if table_match:
        return table_match.group(1).strip()
    return text.strip()



def write_report_header(output_file, args: argparse.Namespace) -> None:
    """Write a small metadata block at the top of the generated report."""
    output_file.write("# Vulnerability Test Procedures\n\n")
    output_file.write(f"- Security analysis: `{args.security_md}`\n")
    output_file.write(f"- Connection details: `{args.details_txt}`\n")
    output_file.write(f"- Model: `{args.model}`\n\n")



def generate_report(args: argparse.Namespace) -> None:
    """Main report-generation workflow."""
    rows = parse_security_md(args.security_md)
    contexts = parse_connection_contexts(args.details_txt)
    client = build_client(args.api_key, args.base_url)

    selected_rows = [
        row
        for row in rows
        if args.include_non_vulnerable or is_vulnerability_detected(row.payload)
    ]

    with open(args.output, "w", encoding="utf-8") as output_file:
        write_report_header(output_file, args)

        for index, row in enumerate(selected_rows, start=1):
            key = (row.from_id, row.to_id)
            context = contexts.get(key)
            if context is None:
                print(f"[WARN] Missing connection context for {row.from_id}->{row.to_id}")
                continue

            print(
                f"[{index}/{len(selected_rows)}] "
                f"{row.from_id}->{row.to_id} ({row.attack})"
            )
            try:
                raw_table = request_test_table(
                    client=client,
                    model_name=args.model,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    attack=row.attack,
                    context=context,
                    payload=row.payload,
                )
                table = normalize_table_output(raw_table)
            except Exception as exc:  # noqa: BLE001
                table = f"Generation failed: {exc}"

            output_file.write(
                f"## Event {row.from_id} -> Event {row.to_id} ({row.attack})\n\n"
            )
            output_file.write("### Analysis Context\n\n")
            output_file.write("```json\n")
            output_file.write(json.dumps(row.payload, ensure_ascii=False, indent=2))
            output_file.write("\n```\n\n")
            output_file.write("### Test Procedure\n\n")
            output_file.write(table)
            output_file.write("\n\n")
            output_file.flush()

    print(f"Done. Report written to {args.output}")



def main() -> None:
    """CLI entry point."""
    args = parse_args()
    validate_args(args)
    generate_report(args)


if __name__ == "__main__":
    main()
