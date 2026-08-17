"""Extract SCA representations from specification sentences with DeepSeek.

This script reads one sentence per line from a text file, sends each sentence to a
DeepSeek chat model, and writes a normalized SCA-style output file.

"""

from __future__ import annotations

import argparse
import os
import re
import time
from typing import Optional, TextIO

from openai import OpenAI

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL_NAME = "deepseek-reasoner"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 512
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SEC = 2.0
UNKNOWN_SECTION = "Unknown Section"
FIELD_DEFAULT = "Not specified"
SECTION_RE = re.compile(r"^(\d+(?:\.[\dA-Za-z]+)+)(?:\s|$)")
NUMBERED_ITEM_RE = re.compile(r"^\d+\)")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for local or CI-friendly execution."""
    parser = argparse.ArgumentParser(
        description="Extract SCA representations from a sentence-per-line text file."
    )
    parser.add_argument("--input", required=True, help="Path to the input text file.")
    parser.add_argument("--output", required=True, help="Path to the output text file.")
    parser.add_argument(
        "--api-key",
        default=os.getenv("DEEPSEEK_API_KEY"),
        help="DeepSeek API key. Defaults to the DEEPSEEK_API_KEY environment variable.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL_NAME),
        help=f"Model name. Defaults to {DEFAULT_MODEL_NAME}.",
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
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Maximum retry attempts. Defaults to {DEFAULT_MAX_RETRIES}.",
    )
    parser.add_argument(
        "--retry-backoff-sec",
        type=float,
        default=DEFAULT_RETRY_BACKOFF_SEC,
        help=(
            "Base retry backoff in seconds; actual wait time is multiplied by the "
            "attempt number."
        ),
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Fail early on missing credentials or obviously invalid paths."""
    if not args.api_key:
        raise ValueError(
            "Missing DeepSeek API key. Set DEEPSEEK_API_KEY or pass --api-key."
        )

    if not os.path.isfile(args.input):
        raise FileNotFoundError(f"Input file not found: {args.input}")

    output_dir = os.path.dirname(os.path.abspath(args.output)) or "."
    os.makedirs(output_dir, exist_ok=True)



def build_client(api_key: str, base_url: str) -> OpenAI:
    """Create an OpenAI-compatible client configured for DeepSeek."""
    return OpenAI(api_key=api_key, base_url=base_url)



def detect_section(line: str) -> Optional[str]:
    """Return a normalized section label when a line looks like a section heading."""
    match = SECTION_RE.match(line.strip())
    return f"Section {match.group(1)}" if match else None



def construct_prompt(sentence: str, event_id: int, section_context: Optional[str]) -> str:
    """Build the extraction prompt for a single sentence."""
    section_info = (
        f"(Derived from {section_context})"
        if section_context
        else f"(Derived from {UNKNOWN_SECTION})"
    )
    return f'''You are a TECHNICAL SPECIFICATION expert specializing in 3GPP TS 24.501, TS 38.331 and TS 24.301. Your
task is to analyze the given sentence and extract a SCA node.

SCA node format:
Event ID: {event_id} {section_info}
Sentence: "{sentence}"
Start State: <Representing the initial system state before the transition.>
Condition: <Denoting the triggering clause or prerequisite specified in the specification.>
Action: <Describing the operation mandated by the specification once the condition is satisfied.>
End State: <Indicating the resulting system state after the action is executed.>

Rules:
1. Each sentence corresponds to exactly ONE SCA node.
2. Fill in all fields (Start State, Condition, Action, End State).
   - If the sentence only serves as a structural heading, use "Not specified" for all fields.
   - If a field is unclear, use "Not explicitly defined" instead of leaving it blank.
3. Retain all 3GPP references (e.g., "as specified in subclause X.Y.Z").
4. Do NOT rephrase the sentence; keep it as provided.
5. Follow the output format exactly.

Example:
1. Input Sentence: The non-access stratum (NAS) described in the present document forms the highest stratum of the control plane between UE and AMF (reference point "N1" see 3GPPTS23.501[8]) for both 3GPP and non-3GPP access.

Expected Output:
Event ID: 5 (Derived from Section 4.1)
Sentence: "The non-access stratum (NAS) described in the present document forms the highest stratum of the control plane between UE and AMF (reference point "N1" see 3GPPTS23.501[8]) for both 3GPP and non-3GPP access"
Start State: UE and AMF are not explicitly connected at the NAS level.
Condition: UE needs to communicate with AMF using NAS procedures.
Action: Define NAS as the highest control plane layer and establish its role in UE-AMF interaction.
End State: NAS is identified as the highest control plane stratum for both 3GPP and non-3GPP access.

2. Input Sentence: If required by operator policy, the AMF shall include the NSSAI inclusion mode IE in the REGISTRATION ACCEPT message (see table 4.6.2.3.1 of subclause 4.6.2.3). Upon receipt of the REGISTRATION ACCEPT message.

Expected Output:
Event ID: 5675 (Derived from Section 5.5.1.3.4)
Sentence: "If required by operator policy, the AMF shall include the NSSAI inclusion mode IE in the REGISTRATION ACCEPT message (see table 4.6.2.3.1 of subclause 4.6.2.3). Upon receipt of the REGISTRATION ACCEPT message"
Start State: The UE has sent a REGISTRATION REQUEST message to the AMF, and the AMF is processing the registration request.
Condition: Operator policy requires the inclusion of the NSSAI inclusion mode IE in the REGISTRATION ACCEPT message.
Action: The AMF includes the NSSAI inclusion mode IE in the REGISTRATION ACCEPT message as specified in table 4.6.2.3.1 of subclause 4.6.2.3.
End State: The REGISTRATION ACCEPT message, containing the NSSAI inclusion mode IE, is sent to the UE.

Now process the following sentence:
"{sentence}"

Expected Output Format:
Event ID: {event_id} {section_info}
Sentence: "{sentence}"
Start State:
Condition:
Action:
End State:
'''



def call_deepseek_reasoner(
    client: OpenAI,
    prompt: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
    retry_backoff_sec: float,
) -> str:
    """Call the model with retry handling for transient API failures."""
    last_err: Optional[Exception | RuntimeError] = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if not response or not getattr(response, "choices", None):
                last_err = RuntimeError("Empty response or no choices returned.")
            else:
                message = response.choices[0].message.content
                if message:
                    return message.strip()
                last_err = RuntimeError("Response contained an empty message body.")
        except Exception as exc:  # noqa: BLE001
            last_err = exc

        time.sleep(retry_backoff_sec * attempt)

    raise RuntimeError(f"DeepSeek API failed after {max_retries} retries: {last_err}")



def extract_text(generated_output: str) -> dict[str, str]:
    """Parse the model output into the four SCA fields we persist."""
    extracted = {
        "Start State": FIELD_DEFAULT,
        "Condition": FIELD_DEFAULT,
        "Action": FIELD_DEFAULT,
        "End State": FIELD_DEFAULT,
    }

    for raw_line in generated_output.strip().splitlines():
        line = raw_line.strip()
        if line.startswith("Start State:"):
            extracted["Start State"] = line[len("Start State:") :].strip()
        elif line.startswith("Condition:"):
            extracted["Condition"] = line[len("Condition:") :].strip()
        elif line.startswith("Action:"):
            extracted["Action"] = line[len("Action:") :].strip()
        elif line.startswith("End State:"):
            extracted["End State"] = line[len("End State:") :].strip()

    return extracted



def analyze_sentence(
    client: OpenAI,
    sentence: str,
    out_fp: TextIO,
    event_id: int,
    section_context: Optional[str],
    model_name: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
    retry_backoff_sec: float,
) -> bool:
    """Generate and write one SCA event block for a sentence."""
    prompt = construct_prompt(sentence, event_id, section_context)
    output_text = call_deepseek_reasoner(
        client=client,
        prompt=prompt,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=max_retries,
        retry_backoff_sec=retry_backoff_sec,
    )
    info = extract_text(output_text)

    out_fp.write(f"Event ID: {event_id} (Derived from {section_context or UNKNOWN_SECTION})\n")
    out_fp.write(f'Sentence: "{sentence}"\n')
    out_fp.write(f"Start State: {info['Start State']}\n")
    out_fp.write(f"Condition: {info['Condition']}\n")
    out_fp.write(f"Action: {info['Action']}\n")
    out_fp.write(f"End State: {info['End State']}\n")
    out_fp.write("=" * 60 + "\n")
    return True



def process_file(
    client: OpenAI,
    input_path: str,
    output_path: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
    retry_backoff_sec: float,
) -> None:
    """Read input sentences, track section context, and write extracted events."""
    with open(input_path, "r", encoding="utf-8") as input_file:
        sentences = [line.strip() for line in input_file if line.strip()]

    event_id = 1
    current_section = UNKNOWN_SECTION

    with open(output_path, "w", encoding="utf-8") as out_file:
        for line in sentences:
            detected_section = detect_section(line)
            if detected_section:
                print(f"[Section] {detected_section}")
                current_section = detected_section

            # Skip lines that look like standalone numbered list markers such as "12)".
            if NUMBERED_ITEM_RE.match(line):
                continue

            ok = analyze_sentence(
                client=client,
                sentence=line,
                out_fp=out_file,
                event_id=event_id,
                section_context=current_section,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                max_retries=max_retries,
                retry_backoff_sec=retry_backoff_sec,
            )
            if ok:
                print(f"[Event {event_id}] ({current_section}) {line[:80]}...")
                event_id += 1

    print(f"\nAll events processed. Results saved to '{output_path}'.")



def main() -> None:
    """CLI entry point."""
    args = parse_args()
    validate_args(args)

    client = build_client(api_key=args.api_key, base_url=args.base_url)

    print(f"\nProcessing '{args.input}' ...")
    process_file(
        client=client,
        input_path=args.input,
        output_path=args.output,
        model_name=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        max_retries=args.max_retries,
        retry_backoff_sec=args.retry_backoff_sec,
    )
    print(f"Completed. Results saved to '{args.output}'.")


if __name__ == "__main__":
    main()
