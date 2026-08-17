"""Run LLM-based security analysis over protocol connection files.

This script reads connection-detail files, asks a DeepSeek model to evaluate
multiple attack classes for each connection, and writes the results to Markdown.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from typing import Iterable

from openai import OpenAI

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 4096
ATTACK_TYPES = ("Inject", "Drop", "Modify", "Replay")
CONNECTION_SEPARATOR = "=== Connection: "
OUTPUT_TABLE_HEADER = "| From Event | To Event | Attack Type | Analysis |\n| --- | --- | --- | --- |\n"

SECURITY_REQUIREMENTS = {
    1: "Authentication: Ensures that only legitimate users can access the protocol.",
    2: "Message Integrity: Ensures that messages remain unaltered during communication.",
    3: "Message Confidentiality: Prevents sensitive information from being exposed.",
    4: "Session Key Update: Validates the mechanisms for updating encryption keys.",
    5: "Replay Attack Protection: Prevents attackers from reusing old communication messages.",
    6: "Denial of Service (DoS) Protection: Verifies the network's ability to defend against resource exhaustion attacks.",
    7: "Time Synchronization Attack Protection: Detects whether protocols are vulnerable to time-based attacks.",
    8: "Protocol Compatibility: Ensures correct interaction between multiple generations of protocols.",
    9: "Error Recovery Mechanisms: Examines the ability of the protocol to recover after communication errors.",
    10: "Privacy Protection Mechanisms: Prevents user identity and location information from being leaked.",
    11: "Network Device Authentication: Verifies the legitimacy of network devices.",
    12: "State Consistency: Ensures logical consistency between the states of the FSM.",
    13: "Resource Control: Validates that resource allocation is properly controlled.",
    14: "Communication Retry Mechanism: Ensures correct retry mechanisms after communication failures.",
    15: "Multipath Protection: Detects potential vulnerabilities in multipath communications.",
    16: "Context Switching Consistency: Verifies the correctness of state transitions during context switching.",
    17: "Offline Attack Protection: Ensures the protocol's security in offline scenarios.",
    18: "Key Management Mechanisms: Checks whether key generation, distribution, and destruction meet security standards.",
    19: "Signaling Storm Protection: Prevents the misuse of signaling messages.",
    20: "Protocol Downgrade Attack Protection: Prevents attackers from forcing the protocol to downgrade to an insecure version.",
    21: "Subscriber Concealed Identifier (SUCI) Protection: Detects privacy risks associated with 5G SUCI.",
    22: "Unsecured Clock Source Attack Protection: Validates whether the protocol relies on unsecured clock sources.",
    23: "Signaling Exhaustion Attack Protection: Prevents attacks that exhaust signaling resources.",
    24: "Segmented Packet Attack Protection: Detects vulnerabilities in segmented packets within transport layer protocols.",
    25: "Network Device Behavior Consistency: Verifies whether different device implementations meet protocol expectations.",
    26: "Protocol Implementation Flaw Detection: Identifies vulnerabilities caused by differences in protocol implementation.",
    27: "5G-specific New Attack Scenarios: Captures undocumented attack scenarios unique to 5G.",
    28: "Rogue Base Station (Fake gNodeB) Detection: Verifies that the network and UEs can detect and avoid unauthorized or fake base stations.",
    29: "Handover Security and Integrity: Ensures secure procedures and integrity checks during cell/technology handovers.",
    30: "Network Slicing Isolation: Validates that security boundaries between different 5G slices are strictly enforced.",
    31: "RAN-level Security Checks: Focuses on the radio protocol layer security, including ciphering and integrity checks.",
    32: "HSM and Secure Element Integration: Ensures that hardware security modules or secure elements protect cryptographic keys.",
    33: "Quantum-resistant Cryptography Preparations: Evaluates readiness for future quantum-resistant encryption algorithms.",
    34: "Eavesdropping and Side-channel Attack Protection: Detects vulnerabilities allowing passive interception or metadata leakage.",
    35: "Billing and Fraud Protection: Prevents fraudulent usage or manipulation of charging records.",
    36: "Roaming and Inter-PLMN Security: Ensures secure inter-operator interfaces and consistent security policies.",
    37: "Secure Software/Firmware Update Mechanisms: Verifies that updates for UEs and network elements are signed, verified, and protected against rollbacks.",
    38: "5G Core Network Function Isolation: Checks isolation between service-based architecture functions.",
    39: "Supply Chain Security: Evaluates the trustworthiness of hardware/software from external vendors and prevents hidden backdoors.",
    40: "Intrusion Detection and Logging Mechanisms: Ensures real-time monitoring and accurate logging of security events.",
    41: "Secure API Exposure in 5G SBA: Checks that all 5G core service-based interfaces have robust authentication, authorization, and input validation.",
    42: "Lawful Interception Controls: Ensures lawful interception features are secured, controlled, and do not leak user data to unauthorized entities.",
    43: "Physical Layer Attacks (Jamming, Spoofing): Tests resilience against RF jamming, signal spoofing, and other radio-level denial techniques.",
    44: "Mobility Management Integrity: Validates correctness of attach/detach, location updates, and paging procedures.",
    45: "User Plane Integrity Protection: Ensures user-plane traffic has integrity checks to detect tampering at the 5G core and beyond.",
    46: "Cross-layer or Cross-protocol Attack Vectors: Examines vulnerabilities arising from interactions between different protocol layers.",
    47: "Configuration Management and Hardening: Checks that network elements follow secure defaults and are not misconfigured.",
    48: "IoT Device Security: Verifies that resource-constrained IoT devices comply with minimal cryptographic and security standards.",
    49: "Fallback/Inter-RAT Attacks: Prevents forced fallback to older, less secure radio access technologies.",
    50: "UE-based Attacks and Security Settings: Evaluates end-user device behavior, ensuring it does not inadvertently enable impersonation or data leakage.",
    51: "Policy Control and Charging Function Security: Guards against manipulation of policy or QoS rules.",
    52: "Session Continuity Attacks: Ensures attackers cannot hijack or forcibly terminate ongoing sessions during network transitions.",
}


@dataclass
class EventFields:
    """Fields extracted from one event description block."""

    start_state: str
    condition: str
    action: str
    end_state: str


@dataclass
class Connection:
    """Connection between two events to be evaluated for attack viability."""

    from_id: int
    to_id: int
    from_event: EventFields
    to_event: EventFields



def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Evaluate security risks for protocol connection files with DeepSeek."
    )
    parser.add_argument(
        "--job",
        nargs=2,
        metavar=("INPUT", "OUTPUT"),
        action="append",
        required=True,
        help="Input/output pair. Repeat this option to process multiple files.",
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
    return parser.parse_args()



def validate_args(args: argparse.Namespace) -> None:
    """Fail early on missing credentials or invalid input paths."""
    if not args.api_key:
        raise ValueError(
            "Missing DeepSeek API key. Set DEEPSEEK_API_KEY or pass --api-key."
        )

    for input_path, output_path in args.job:
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        os.makedirs(output_dir, exist_ok=True)



def extract_field(text: str, field_name: str) -> str:
    """Extract one labeled field from a connection sub-block."""
    match = re.search(rf"{re.escape(field_name)}:\s*(.*)", text)
    return match.group(1).strip() if match else "Unknown"



def parse_event_block(text: str) -> EventFields:
    """Convert a raw event block into a structured event object."""
    return EventFields(
        start_state=extract_field(text, "Start State"),
        condition=extract_field(text, "Condition"),
        action=extract_field(text, "Action"),
        end_state=extract_field(text, "End State"),
    )



def parse_connections(input_text: str) -> list[Connection]:
    """Parse all connection entries from a connection-detail file."""
    connections: list[Connection] = []

    for block in input_text.split(CONNECTION_SEPARATOR)[1:]:
        try:
            ids = block.split(" ===", maxsplit=1)[0]
            from_id, to_id = map(int, ids.split(" -> "))

            from_block = block.split("From Event (", maxsplit=1)[1].split(
                "To Event (", maxsplit=1
            )[0]
            to_block = block.split("To Event (", maxsplit=1)[1].split(
                "========================================", maxsplit=1
            )[0]

            connections.append(
                Connection(
                    from_id=from_id,
                    to_id=to_id,
                    from_event=parse_event_block(from_block),
                    to_event=parse_event_block(to_block),
                )
            )
        except (IndexError, ValueError) as exc:
            print(f"Skipping unparsable connection block: {exc}")

    return connections



def build_security_requirement_list() -> str:
    """Render requirement identifiers into a concise prompt section."""
    return "\n".join(
        f"  {requirement_id}. {description.split(':', maxsplit=1)[0]}"
        for requirement_id, description in SECURITY_REQUIREMENTS.items()
    )



def generate_prompt(connection: Connection, attack_type: str) -> str:
    """Build the evaluation prompt for one connection/attack pair."""
    security_requirement_list = build_security_requirement_list()
    from_event = connection.from_event
    to_event = connection.to_event

    return f"""You are a senior 4G/5G NAS security analyst.
Analyze the following protocol state transition and determine whether a(n) {attack_type} attack could introduce a realistic and meaningful security vulnerability.

From Event (ID: {connection.from_id}):
  - Start State: {from_event.start_state}
  - Condition: {from_event.condition}
  - Action: {from_event.action}
  - End State: {from_event.end_state}

To Event (ID: {connection.to_id}):
  - Start State: {to_event.start_state}
  - Condition: {to_event.condition}
  - Action: {to_event.action}
  - End State: {to_event.end_state}

Attack scenario: A(n) {attack_type} attack may occur at some point between these transitions.

Actor, message-direction, and replay-scope rules:
- Before describing an attack effect, infer the sender, receiver, and affected state machine for the attacked message.
- Use the actual receiver of the attacked message as the subject of message processing.
- A replay attack may target any message transmitted in the transition, including UE-to-network and network-to-UE messages.
- Do not require the replayed message to trigger the sender's own state transition.
- For a replayed UE-originated message, analyze whether the receiving network entity may accept, process, or be disrupted by the stale duplicate.
- For a replayed network-originated message, analyze whether the receiving UE may accept, process, or be disrupted by the stale duplicate.
- If the original transition is caused by an internal condition, this does not rule out replay of messages sent as part of that transition.
- If the sender, receiver, or protection status is unclear, state the uncertainty instead of assuming the attack is impossible.

Security-context and protection-status rules:
- Do not assume that a protocol message is integrity-protected, ciphered, or replay-protected merely because it is part of NAS/IMS signaling.
- Before dismissing a replay/modify/inject attack, determine whether a valid security context, freshness mechanism, and integrity verification are explicitly active in the given transition.
- Pay special attention to transitions involving registration, service request, idle/connected switching, security context establishment, or security mode procedures, where protection may be absent, partial, stale, or not yet validated.
- If the transition does not explicitly show that integrity and freshness checks are active before message processing, do not use them as the sole reason to mark the attack as non-vulnerable.
- Distinguish between protection that exists in the protocol in general and protection that is actually available at this transition point.

Relevant security requirements:
{security_requirement_list}

Evaluation criteria:
- Respond with \"vulnerability_detected\": \"Yes\" only if the attack introduces a realistic vulnerability with observable consequences.
- Vulnerabilities may include authentication bypass, integrity protection failure, state inconsistency, session hijacking, denial of service, or replay that causes real state divergence.
- Do not respond \"Yes\" merely because a message is optional or dropped, but if this optional handling creates inconsistencies, opens the door to spoofed messages, or breaks expected session behavior, then you must consider it a vulnerability.

Return your answer strictly in the following JSON format:

BEGIN_JSON
{{
  \"vulnerability_detected\": \"Yes\" or \"No\",
  \"violated_requirements\": [list of integers],
  \"explanation\": \"short explanation\",
  \"issue_classification\": \"Protocol Design Issue\" or \"Implementation Issue\" or \"Both\" or \"N/A\",
  \"test_case\": \"short string or 'N/A'\",
  \"vulnerability_source\": \"event{connection.from_id}\" or \"event{connection.to_id}\" or \"event{connection.from_id} and event{connection.to_id}\" or \"unclear\"
}}
END_JSON
"""



def request_analysis(
    client: OpenAI,
    connection: Connection,
    attack_type: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call the model and return the raw response text."""
    prompt = generate_prompt(connection, attack_type)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a cellular security expert."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()



def extract_json_payload(response_text: str) -> str:
    """Normalize the model response into pretty JSON when possible."""
    fenced_match = re.search(
        r"BEGIN_JSON\s*(\{.*?\})\s*END_JSON",
        response_text,
        re.DOTALL,
    )
    json_blob = fenced_match.group(1) if fenced_match else None

    if json_blob is None:
        fallback_match = re.search(r"(\{.*\})", response_text, re.DOTALL)
        if fallback_match:
            json_blob = fallback_match.group(1)

    if json_blob is None:
        return response_text

    try:
        parsed = json.loads(json_blob)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return response_text



def format_analysis_cell(response_text: str) -> str:
    """Format model output as a Markdown-friendly table cell."""
    normalized = extract_json_payload(response_text)
    if normalized.lstrip().startswith("{"):
        cell_content = f"```json\n{normalized}\n```"
    else:
        cell_content = normalized
    return cell_content.replace("|", r"\|")



def write_output_header(output_file) -> None:
    """Write the Markdown table header once per output file."""
    output_file.write(OUTPUT_TABLE_HEADER)



def run_analysis_for_job(
    client: OpenAI,
    input_path: str,
    output_path: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
) -> None:
    """Process one input/output pair and write the Markdown report."""
    with open(input_path, "r", encoding="utf-8") as input_file:
        connections = parse_connections(input_file.read())

    with open(output_path, "w", encoding="utf-8") as output_file:
        write_output_header(output_file)

        for index, connection in enumerate(connections, start=1):
            for attack_type in ATTACK_TYPES:
                print(
                    f"[{os.path.basename(input_path)}] "
                    f"[{index}/{len(connections)}] "
                    f"{connection.from_id}->{connection.to_id} ({attack_type})"
                )
                try:
                    response_text = request_analysis(
                        client=client,
                        connection=connection,
                        attack_type=attack_type,
                        model_name=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                except Exception as exc:  # noqa: BLE001
                    response_text = f"API Error: {exc}"

                row = (
                    f"| {connection.from_id} | {connection.to_id} | {attack_type} | "
                    f"{format_analysis_cell(response_text)} |\n"
                )
                output_file.write(row)
                output_file.flush()

    print(f"Done. Results saved to {output_path}")



def run_jobs(args: argparse.Namespace) -> None:
    """Create a client and execute all configured analysis jobs."""
    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    for input_path, output_path in args.job:
        run_analysis_for_job(
            client=client,
            input_path=input_path,
            output_path=output_path,
            model_name=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )



def main() -> None:
    """CLI entry point."""
    args = parse_args()
    validate_args(args)
    run_jobs(args)


if __name__ == "__main__":
    main()
